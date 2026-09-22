import json

from loguru import logger

from app.kubernetes.kubectl import run_kubectl
from app.models.investigation import DeploymentInspection, UnhealthyDeployment


def inspect_deployments() -> DeploymentInspection:
    result = run_kubectl("get", "deployments", "-A", "-o", "json")
    if not result.success:
        return DeploymentInspection(
            healthy=False,
            unhealthy_deployments=[],
            total_deployments=0,
            error=result.error,
        )

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse deployments JSON: {}", exc)
        return DeploymentInspection(
            healthy=False,
            unhealthy_deployments=[],
            total_deployments=0,
            error="failed to parse kubectl deployment output",
        )

    unhealthy: list[UnhealthyDeployment] = []
    items = payload.get("items") or []

    for item in items:
        metadata = item.get("metadata") or {}
        spec = item.get("spec") or {}
        status = item.get("status") or {}
        name = metadata.get("name") or "unknown"
        namespace = metadata.get("namespace") or "default"
        desired = int(spec.get("replicas") or 0)
        available = int(status.get("availableReplicas") or 0)
        unavailable = int(status.get("unavailableReplicas") or 0)
        updated = int(status.get("updatedReplicas") or 0)
        ready = int(status.get("readyReplicas") or 0)

        condition_summaries: list[str] = []
        rollout_failed = False
        progressing_stalled = False

        for condition in status.get("conditions") or []:
            cond_type = condition.get("type") or "Unknown"
            cond_status = condition.get("status") or "Unknown"
            cond_reason = condition.get("reason") or ""
            cond_message = condition.get("message") or ""
            summary = f"{cond_type}={cond_status}"
            if cond_reason:
                summary = f"{summary} ({cond_reason})"
            if cond_message:
                summary = f"{summary}: {cond_message}"
            condition_summaries.append(summary)

            if cond_type == "Progressing" and cond_status == "False":
                progressing_stalled = True
            if cond_reason in {"ProgressDeadlineExceeded", "ReplicaSetCreateError"}:
                rollout_failed = True
            if cond_type == "Available" and cond_status == "False" and desired > 0:
                rollout_failed = True

        is_unhealthy = (
            unavailable > 0
            or available < desired
            or ready < desired
            or (desired > 0 and updated < desired)
            or rollout_failed
            or progressing_stalled
        )

        if is_unhealthy:
            unhealthy.append(
                UnhealthyDeployment(
                    name=name,
                    namespace=namespace,
                    desired_replicas=desired,
                    available_replicas=available,
                    unavailable_replicas=unavailable,
                    conditions=condition_summaries,
                )
            )

    logger.info(
        "Deployment inspection complete: {} deployments, {} unhealthy",
        len(items),
        len(unhealthy),
    )
    return DeploymentInspection(
        healthy=len(unhealthy) == 0,
        unhealthy_deployments=unhealthy,
        total_deployments=len(items),
    )

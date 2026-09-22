import json
from datetime import datetime, timezone

from loguru import logger

from app.kubernetes.kubectl import run_kubectl
from app.models.investigation import PodInspection, ProblematicPod

UNHEALTHY_PHASES = {"Failed", "Unknown"}
UNHEALTHY_REASONS = {
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "Error",
    "OOMKilled",
    "CreateContainerConfigError",
    "InvalidImageName",
    "CreateContainerError",
    "RunContainerError",
}
STUCK_PENDING_SECONDS = 120
STUCK_CONTAINER_CREATING_SECONDS = 120


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _age_seconds(timestamp: str | None) -> float | None:
    started = _parse_iso8601(timestamp)
    if started is None:
        return None
    now = datetime.now(timezone.utc)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return (now - started).total_seconds()


def _container_problem(container: dict) -> tuple[str, str] | None:
    state = container.get("state") or {}
    waiting = state.get("waiting") or {}
    terminated = state.get("terminated") or {}
    last_state = container.get("lastState") or {}
    last_terminated = last_state.get("terminated") or {}

    waiting_reason = waiting.get("reason") or ""
    if waiting_reason in UNHEALTHY_REASONS:
        return waiting_reason, waiting.get("message") or waiting_reason

    terminated_reason = terminated.get("reason") or ""
    if terminated_reason in UNHEALTHY_REASONS:
        return terminated_reason, terminated.get("message") or terminated_reason

    last_reason = last_terminated.get("reason") or ""
    if last_reason in UNHEALTHY_REASONS:
        return last_reason, last_terminated.get("message") or last_reason

    if waiting_reason == "ContainerCreating":
        return "ContainerCreating", waiting.get("message") or "ContainerCreating"

    return None


def inspect_pods() -> PodInspection:
    result = run_kubectl("get", "pods", "-A", "-o", "json")
    if not result.success:
        return PodInspection(
            healthy=False,
            problematic_pods=[],
            total_pods=0,
            error=result.error,
        )

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse pod list JSON: {}", exc)
        return PodInspection(
            healthy=False,
            problematic_pods=[],
            total_pods=0,
            error="failed to parse kubectl pod output",
        )

    items = payload.get("items") or []
    problematic: list[ProblematicPod] = []

    for item in items:
        metadata = item.get("metadata") or {}
        status = item.get("status") or {}
        name = metadata.get("name") or "unknown"
        namespace = metadata.get("namespace") or "default"
        phase = status.get("phase") or "Unknown"
        start_time = status.get("startTime") or metadata.get("creationTimestamp")
        age = _age_seconds(start_time)

        container_statuses = status.get("containerStatuses") or []
        init_statuses = status.get("initContainerStatuses") or []
        found_reason: str | None = None
        found_message: str | None = None

        for container in [*init_statuses, *container_statuses]:
            problem = _container_problem(container)
            if problem is None:
                continue
            found_reason, found_message = problem
            if found_reason != "ContainerCreating":
                break

        if found_reason == "ContainerCreating":
            if age is None or age >= STUCK_CONTAINER_CREATING_SECONDS:
                problematic.append(
                    ProblematicPod(
                        name=name,
                        namespace=namespace,
                        status="ContainerCreating",
                        reason="ContainerCreating",
                        message=found_message or "ContainerCreating appears stuck",
                    )
                )
            continue

        if found_reason:
            problematic.append(
                ProblematicPod(
                    name=name,
                    namespace=namespace,
                    status=found_reason,
                    reason=found_reason,
                    message=found_message,
                )
            )
            continue

        if phase == "Pending":
            if age is None or age >= STUCK_PENDING_SECONDS:
                conditions = status.get("conditions") or []
                pending_message = None
                for condition in conditions:
                    if condition.get("type") == "PodScheduled" and condition.get("status") != "True":
                        pending_message = condition.get("message") or condition.get("reason")
                        break
                problematic.append(
                    ProblematicPod(
                        name=name,
                        namespace=namespace,
                        status="Pending",
                        reason="Pending",
                        message=pending_message or "Pod is pending",
                    )
                )
            continue

        if phase in UNHEALTHY_PHASES:
            problematic.append(
                ProblematicPod(
                    name=name,
                    namespace=namespace,
                    status=phase,
                    reason=status.get("reason") or phase,
                    message=status.get("message"),
                )
            )

    logger.info(
        "Pod inspection complete: {} pods, {} problematic",
        len(items),
        len(problematic),
    )
    return PodInspection(
        healthy=len(problematic) == 0,
        problematic_pods=problematic,
        total_pods=len(items),
    )

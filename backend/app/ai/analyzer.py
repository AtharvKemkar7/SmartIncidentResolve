from app.ai.confidence import calibrate_confidence
from app.models.diagnosis import Diagnosis
from app.models.investigation import InvestigationPayload


def diagnosis_from_llm_payload(raw: dict, investigation: InvestigationPayload) -> Diagnosis:
    diagnosis = Diagnosis(
        root_cause=_text(raw.get("root_cause"), "Unable to determine a specific root cause."),
        explanation=_text(raw.get("explanation"), "The model did not provide a detailed explanation."),
        fix=_text(raw.get("fix"), "Re-run investigation after verifying cluster access."),
        kubectl_command=_text(raw.get("kubectl_command"), "kubectl get pods -A"),
        prevention=_text(raw.get("prevention"), "Collect more evidence before making cluster changes."),
        confidence=_confidence(raw.get("confidence")),
        confidence_reasoning=_text(raw.get("confidence_reasoning"), ""),
    )
    return calibrate_confidence(diagnosis, investigation)


def fallback_diagnosis(investigation: InvestigationPayload, reason: str) -> Diagnosis:
    kubectl_errors = [
        investigation.pods.error,
        investigation.events.error,
        investigation.deployments.error,
        investigation.network.error,
    ]
    kubectl_failed = any(kubectl_errors)

    if kubectl_failed:
        root_cause = "Unable to connect to Kubernetes cluster."
        explanation = (
            "Please verify:\n"
            "- kubeconfig path\n"
            "- cluster access\n"
            "- kubectl permissions"
        )
        fix = "Install kubectl, set KUBECONFIG_PATH, and confirm the backend can reach the cluster."
        kubectl_command = "kubectl get pods -A"
        prevention = "Keep a valid kubeconfig available to the backend before investigating incidents."
        confidence = 20
    elif investigation.pods.problematic_pods:
        pod = investigation.pods.problematic_pods[0]
        log_lines = next(
            (item.lines for item in investigation.logs.items if item.name == pod.name),
            [],
        )
        log_hint = " ".join(log_lines[:3]).strip()
        root_cause = f"Pod {pod.namespace}/{pod.name} is unhealthy ({pod.status})."
        explanation = log_hint or pod.message or "The pod is failing, but logs did not include a clearer signal."
        fix = f"Inspect {pod.namespace}/{pod.name} and address the {pod.status} condition."
        kubectl_command = (
            f"kubectl describe pod {pod.name} -n {pod.namespace} && "
            f"kubectl logs {pod.name} -n {pod.namespace} --tail=80"
        )
        prevention = "Add readiness/liveness probes and alert on CrashLoopBackOff and ImagePullBackOff."
        confidence = 55
    elif investigation.deployments.unhealthy_deployments:
        deployment = investigation.deployments.unhealthy_deployments[0]
        root_cause = (
            f"Deployment {deployment.namespace}/{deployment.name} is not fully available."
        )
        explanation = (
            f"Desired replicas={deployment.desired_replicas}, "
            f"available={deployment.available_replicas}, "
            f"unavailable={deployment.unavailable_replicas}."
        )
        fix = f"Inspect the rollout for {deployment.name} and restore the desired replica count."
        kubectl_command = (
            f"kubectl describe deployment {deployment.name} -n {deployment.namespace} && "
            f"kubectl rollout status deployment/{deployment.name} -n {deployment.namespace}"
        )
        prevention = "Watch deployment conditions and block rollouts that fail availability checks."
        confidence = 50
    elif investigation.network.issues:
        issue = investigation.network.issues[0]
        root_cause = f"Service {issue.namespace}/{issue.service} has a {issue.issue.replace('_', ' ')}."
        explanation = issue.details
        fix = f"Fix the {issue.issue.replace('_', ' ')} on {issue.service}."
        kubectl_command = (
            f"kubectl get svc {issue.service} -n {issue.namespace} -o yaml && "
            f"kubectl get endpoints {issue.service} -n {issue.namespace}"
        )
        prevention = "Validate service selectors against pod labels during deployment."
        confidence = 50
    else:
        root_cause = "No critical Kubernetes issues detected."
        explanation = "Cluster appears healthy."
        fix = "No Kubernetes change is required right now."
        kubectl_command = "kubectl get pods -A && kubectl get events -A --sort-by=.lastTimestamp"
        prevention = "Keep cluster health checks in place so silent failures are easier to catch."
        confidence = 70

    diagnosis = Diagnosis(
        root_cause=root_cause,
        explanation=explanation,
        fix=fix,
        kubectl_command=kubectl_command,
        prevention=prevention,
        confidence=confidence,
        confidence_reasoning=reason,
    )
    return calibrate_confidence(diagnosis, investigation)


def _text(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _confidence(value: object) -> int:
    try:
        score = int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 50
    return max(0, min(100, score))

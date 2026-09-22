from app.models.diagnosis import Diagnosis
from app.models.investigation import InvestigationPayload


def evidence_signals(investigation: InvestigationPayload) -> dict[str, bool]:
    return {
        "kubectl_ok": not any(
            [
                investigation.pods.error,
                investigation.logs.error,
                investigation.events.error,
                investigation.deployments.error,
                investigation.network.error,
            ]
        ),
        "has_pod_failures": bool(investigation.pods.problematic_pods),
        "has_logs": any(item.lines for item in investigation.logs.items),
        "has_events": bool(investigation.events.findings),
        "has_deployment_failures": bool(investigation.deployments.unhealthy_deployments),
        "has_network_issues": bool(investigation.network.issues),
    }


def calibrate_confidence(diagnosis: Diagnosis, investigation: InvestigationPayload) -> Diagnosis:
    signals = evidence_signals(investigation)
    supporting = sum(
        1
        for key, present in signals.items()
        if key != "kubectl_ok" and present
    )
    score = diagnosis.confidence

    if not signals["kubectl_ok"]:
        score = min(score, 35)
    elif supporting >= 3:
        score = max(score, 80)
    elif supporting == 2:
        score = max(min(score, 90), 65)
    elif supporting == 1:
        score = min(max(score, 40), 70)
    else:
        score = min(score, 40)

    score = max(0, min(100, score))
    reasoning = diagnosis.confidence_reasoning.strip()
    if not reasoning:
        parts = []
        if signals["has_pod_failures"]:
            parts.append("unhealthy pod state")
        if signals["has_logs"]:
            parts.append("log excerpts")
        if signals["has_events"]:
            parts.append("cluster events")
        if signals["has_deployment_failures"]:
            parts.append("deployment health")
        if signals["has_network_issues"]:
            parts.append("network findings")
        if not signals["kubectl_ok"]:
            reasoning = "Low confidence because kubectl evidence could not be collected."
        elif parts:
            reasoning = "Confidence based on: " + ", ".join(parts) + "."
        else:
            reasoning = "Limited corroborating evidence was available."

    return diagnosis.model_copy(
        update={"confidence": score, "confidence_reasoning": reasoning}
    )

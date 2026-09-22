import json
from collections import defaultdict

from loguru import logger

from app.kubernetes.kubectl import run_kubectl
from app.models.investigation import EventFinding, EventsInspection

INTERESTING_REASONS = {
    "FailedScheduling",
    "BackOff",
    "FailedMount",
    "FailedPull",
    "ErrImagePull",
    "Unhealthy",
    "Failed",
    "FailedCreate",
    "FailedBinding",
    "InspectFailed",
    "NetworkNotReady",
}


def analyze_events() -> EventsInspection:
    result = run_kubectl("get", "events", "-A", "-o", "json")
    if not result.success:
        return EventsInspection(findings=[], error=result.error)

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse events JSON: {}", exc)
        return EventsInspection(findings=[], error="failed to parse kubectl events output")

    grouped: dict[tuple[str, str, str, str], dict] = defaultdict(
        lambda: {"count": 0, "message": ""}
    )

    for item in payload.get("items") or []:
        reason = item.get("reason") or ""
        if reason not in INTERESTING_REASONS:
            continue

        involved = item.get("involvedObject") or {}
        namespace = item.get("namespace") or involved.get("namespace") or "default"
        kind = involved.get("kind") or "Unknown"
        name = involved.get("name") or "unknown"
        object_ref = f"{kind}/{name}"
        message = item.get("message") or reason
        count = int(item.get("count") or 1)
        key = (reason, namespace, object_ref, message)
        grouped[key]["count"] += count
        grouped[key]["message"] = message

    findings = [
        EventFinding(
            reason=reason,
            count=data["count"],
            namespace=namespace,
            object=object_ref,
            message=data["message"],
        )
        for (reason, namespace, object_ref, message), data in grouped.items()
    ]
    findings.sort(key=lambda finding: finding.count, reverse=True)

    logger.info("Event analysis complete: {} findings", len(findings))
    return EventsInspection(findings=findings[:50])

import json

from loguru import logger

from app.kubernetes.kubectl import run_kubectl
from app.models.investigation import NetworkInspection, NetworkIssue

DNS_KEYWORDS = ("dns", "coredns", "nxdomain", "name resolution", "resolver")


def _labels_match(selector: dict[str, str], labels: dict[str, str]) -> bool:
    if not selector:
        return False
    return all(labels.get(key) == value for key, value in selector.items())


def inspect_network() -> NetworkInspection:
    services_result = run_kubectl("get", "svc", "-A", "-o", "json")
    if not services_result.success:
        return NetworkInspection(issues=[], error=services_result.error)

    try:
        services_payload = json.loads(services_result.stdout or "{}")
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse services JSON: {}", exc)
        return NetworkInspection(issues=[], error="failed to parse kubectl service output")

    endpoints_result = run_kubectl("get", "endpoints", "-A", "-o", "json")
    endpoints_by_key: dict[tuple[str, str], dict] = {}
    if endpoints_result.success:
        try:
            endpoints_payload = json.loads(endpoints_result.stdout or "{}")
            for item in endpoints_payload.get("items") or []:
                metadata = item.get("metadata") or {}
                key = (metadata.get("namespace") or "default", metadata.get("name") or "")
                endpoints_by_key[key] = item
        except json.JSONDecodeError:
            logger.warning("Failed to parse endpoints JSON")

    pods_result = run_kubectl("get", "pods", "-A", "-o", "json")
    pods_by_namespace: dict[str, list[dict]] = {}
    if pods_result.success:
        try:
            pods_payload = json.loads(pods_result.stdout or "{}")
            for item in pods_payload.get("items") or []:
                namespace = (item.get("metadata") or {}).get("namespace") or "default"
                pods_by_namespace.setdefault(namespace, []).append(item)
        except json.JSONDecodeError:
            logger.warning("Failed to parse pods JSON for network inspection")

    issues: list[NetworkIssue] = []
    services = services_payload.get("items") or []

    for service in services:
        metadata = service.get("metadata") or {}
        spec = service.get("spec") or {}
        name = metadata.get("name") or "unknown"
        namespace = metadata.get("namespace") or "default"
        service_type = spec.get("type") or "ClusterIP"
        selector = spec.get("selector") or {}

        if service_type == "ExternalName":
            continue

        if not selector:
            if name.endswith("kubernetes") and namespace == "default":
                continue
            issues.append(
                NetworkIssue(
                    service=name,
                    namespace=namespace,
                    issue="missing_selector",
                    details="Service has no selector; it will not route to pods automatically",
                )
            )
            continue

        namespace_pods = pods_by_namespace.get(namespace) or []
        matching_pods = [
            pod
            for pod in namespace_pods
            if _labels_match(selector, (pod.get("metadata") or {}).get("labels") or {})
        ]
        if not matching_pods:
            issues.append(
                NetworkIssue(
                    service=name,
                    namespace=namespace,
                    issue="selector_mismatch",
                    details=f"No pods match selector {selector}",
                )
            )
            continue

        endpoint = endpoints_by_key.get((namespace, name))
        subsets = (endpoint or {}).get("subsets") or []
        addresses = [
            address
            for subset in subsets
            for address in (subset.get("addresses") or [])
        ]
        if not addresses:
            issues.append(
                NetworkIssue(
                    service=name,
                    namespace=namespace,
                    issue="missing_endpoints",
                    details="Service has matching pods but no ready endpoints",
                )
            )

    events_result = run_kubectl("get", "events", "-A", "-o", "json")
    if events_result.success:
        try:
            events_payload = json.loads(events_result.stdout or "{}")
            for item in events_payload.get("items") or []:
                message = (item.get("message") or "").lower()
                reason = item.get("reason") or ""
                if not any(keyword in message for keyword in DNS_KEYWORDS):
                    continue
                involved = item.get("involvedObject") or {}
                issues.append(
                    NetworkIssue(
                        service=involved.get("name") or "unknown",
                        namespace=item.get("namespace") or involved.get("namespace") or "default",
                        issue="dns",
                        details=item.get("message") or reason,
                    )
                )
        except json.JSONDecodeError:
            logger.warning("Failed to parse events JSON for DNS inspection")

    unique: list[NetworkIssue] = []
    seen: set[tuple[str, str, str, str]] = set()
    for issue in issues:
        key = (issue.namespace, issue.service, issue.issue, issue.details)
        if key in seen:
            continue
        seen.add(key)
        unique.append(issue)

    logger.info("Network inspection complete: {} issues", len(unique))
    return NetworkInspection(issues=unique)

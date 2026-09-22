from app.kubernetes.deployments import inspect_deployments
from app.kubernetes.events import analyze_events
from app.kubernetes.logs import collect_logs
from app.kubernetes.network import inspect_network
from app.kubernetes.pods import inspect_pods
from app.models.investigation import ProblematicPod

__all__ = [
    "inspect_pods",
    "inspect_nodes",
    "inspect_events",
    "inspect_deployments",
    "inspect_network",
    "collect_logs",
]


def inspect_nodes() -> None:
    pass


def inspect_events():
    return analyze_events()


def collect_failed_pod_logs(problematic_pods: list[ProblematicPod]):
    return collect_logs(problematic_pods)

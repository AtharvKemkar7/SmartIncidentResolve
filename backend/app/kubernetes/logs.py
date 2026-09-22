from loguru import logger

from app.kubernetes.kubectl import run_kubectl
from app.models.investigation import LogsInspection, PodLogExcerpt, ProblematicPod

MAX_LOG_LINES = 80
MAX_PODS = 10
FAILURE_KEYWORDS = (
    "exception",
    "error",
    "fatal",
    "panic",
    "traceback",
    "connection refused",
    "connection reset",
    "timeout",
    "timed out",
    "missing",
    "not found",
    "failed",
    "image",
    "unauthorized",
    "permission denied",
    "env",
    "environment",
    "startup",
    "crash",
)


def _is_relevant(line: str) -> bool:
    lowered = line.lower()
    return any(keyword in lowered for keyword in FAILURE_KEYWORDS)


def _select_lines(raw: str) -> list[str]:
    lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
    relevant = [line for line in lines if _is_relevant(line)]
    selected = relevant[-40:] if relevant else lines[-20:]
    return selected[:MAX_LOG_LINES]


def collect_logs(problematic_pods: list[ProblematicPod]) -> LogsInspection:
    if not problematic_pods:
        return LogsInspection(items=[])

    items: list[PodLogExcerpt] = []
    errors: list[str] = []

    for pod in problematic_pods[:MAX_PODS]:
        result = run_kubectl(
            "logs",
            pod.name,
            "-n",
            pod.namespace,
            "--tail",
            str(MAX_LOG_LINES),
            "--all-containers=true",
        )

        if not result.success or not result.stdout.strip():
            previous = run_kubectl(
                "logs",
                pod.name,
                "-n",
                pod.namespace,
                "--tail",
                str(MAX_LOG_LINES),
                "--all-containers=true",
                "--previous",
            )
            if previous.success and previous.stdout.strip():
                result = previous
            elif not result.success:
                errors.append(
                    f"{pod.namespace}/{pod.name}: {result.error or previous.error or 'log fetch failed'}"
                )
                items.append(
                    PodLogExcerpt(
                        name=pod.name,
                        namespace=pod.namespace,
                        status=pod.status,
                        lines=[result.error or "failed to fetch logs"],
                    )
                )
                continue

        items.append(
            PodLogExcerpt(
                name=pod.name,
                namespace=pod.namespace,
                status=pod.status,
                lines=_select_lines(result.stdout),
            )
        )

    logger.info("Collected logs for {} problematic pods", len(items))
    return LogsInspection(
        items=items,
        error="; ".join(errors) if errors else None,
    )

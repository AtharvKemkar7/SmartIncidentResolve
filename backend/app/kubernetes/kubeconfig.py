import os
from pathlib import Path

import yaml
from loguru import logger

from app.core.config import settings
from app.models.clusters import ClusterInfo, ClusterListResponse


def resolve_kubeconfig_path() -> str | None:
    if settings.kubeconfig_path:
        return settings.kubeconfig_path
    env_path = os.environ.get("KUBECONFIG")
    if env_path:
        return env_path.split(os.pathsep)[0]
    default_path = Path.home() / ".kube" / "config"
    if default_path.exists():
        return str(default_path)
    return None


def list_clusters() -> ClusterListResponse:
    path = resolve_kubeconfig_path()
    if not path:
        return ClusterListResponse(
            clusters=[],
            kubeconfig_path=None,
            error=(
                "No kubeconfig found. Set KUBECONFIG_PATH or place a config at ~/.kube/config."
            ),
        )

    config_path = Path(path).expanduser()
    if not config_path.exists():
        return ClusterListResponse(
            clusters=[],
            kubeconfig_path=str(config_path),
            error=f"Kubeconfig not found at {config_path}. Verify the path and cluster access.",
        )

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.error("Failed to read kubeconfig: {}", exc)
        return ClusterListResponse(
            clusters=[],
            kubeconfig_path=str(config_path),
            error="Unable to read kubeconfig. Confirm the file is valid YAML.",
        )

    clusters_by_name = {
        item.get("name"): (item.get("cluster") or {})
        for item in (data.get("clusters") or [])
        if item.get("name")
    }
    current = data.get("current-context")
    clusters: list[ClusterInfo] = []

    for item in data.get("contexts") or []:
        name = item.get("name")
        if not name:
            continue
        context = item.get("context") or {}
        cluster_name = context.get("cluster") or name
        cluster_meta = clusters_by_name.get(cluster_name) or {}
        clusters.append(
            ClusterInfo(
                name=name,
                cluster=cluster_name,
                server=cluster_meta.get("server"),
                namespace=context.get("namespace") or "default",
                current=name == current,
            )
        )

    return ClusterListResponse(
        clusters=clusters,
        kubeconfig_path=str(config_path),
        current_context=current,
        error=None if clusters else "Kubeconfig has no contexts to investigate.",
    )

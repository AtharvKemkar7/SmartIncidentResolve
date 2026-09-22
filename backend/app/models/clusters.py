from pydantic import BaseModel


class ClusterInfo(BaseModel):
    name: str
    cluster: str
    server: str | None = None
    namespace: str = "default"
    current: bool = False


class ClusterListResponse(BaseModel):
    clusters: list[ClusterInfo]
    kubeconfig_path: str | None = None
    current_context: str | None = None
    error: str | None = None

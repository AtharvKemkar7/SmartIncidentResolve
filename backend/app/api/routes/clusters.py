from fastapi import APIRouter

from app.core.security import CurrentUser
from app.kubernetes.kubeconfig import list_clusters
from app.models.clusters import ClusterListResponse

router = APIRouter()


@router.get("/clusters", response_model=ClusterListResponse)
def get_clusters(_user: CurrentUser) -> ClusterListResponse:
    return list_clusters()

from fastapi import APIRouter

from app.core.security import CurrentUser
from app.models.history import HistoryResponse
from app.services.history import load_history

router = APIRouter()


@router.get("/history", response_model=HistoryResponse)
def get_history(_user: CurrentUser) -> HistoryResponse:
    return HistoryResponse(items=load_history())

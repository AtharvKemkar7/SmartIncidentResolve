from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    id: str
    timestamp: str
    cluster: str
    namespace: str
    root_cause: str
    confidence: int = 0
    status: str
    job_id: str | None = None


class HistoryResponse(BaseModel):
    items: list[HistoryItem] = Field(default_factory=list)

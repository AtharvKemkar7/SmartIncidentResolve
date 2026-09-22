from pydantic import BaseModel, Field

from app.models.investigation import InvestigateResponse


class InvestigateRequest(BaseModel):
    cluster: str | None = None


class JobStep(BaseModel):
    id: str
    label: str
    state: str


class JobStartResponse(BaseModel):
    job_id: str
    status: str
    cluster: str | None = None
    steps: list[JobStep] = Field(default_factory=list)


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    cluster: str | None = None
    steps: list[JobStep] = Field(default_factory=list)
    error: str | None = None
    result: InvestigateResponse | None = None

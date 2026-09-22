from pydantic import BaseModel, Field

from app.models.diagnosis import Diagnosis


class ProblematicPod(BaseModel):
    name: str
    namespace: str
    status: str
    reason: str | None = None
    message: str | None = None


class PodInspection(BaseModel):
    healthy: bool
    problematic_pods: list[ProblematicPod] = Field(default_factory=list)
    total_pods: int = 0
    error: str | None = None


class PodLogExcerpt(BaseModel):
    name: str
    namespace: str
    status: str
    lines: list[str] = Field(default_factory=list)


class LogsInspection(BaseModel):
    items: list[PodLogExcerpt] = Field(default_factory=list)
    error: str | None = None


class EventFinding(BaseModel):
    reason: str
    count: int
    namespace: str
    object: str
    message: str


class EventsInspection(BaseModel):
    findings: list[EventFinding] = Field(default_factory=list)
    error: str | None = None


class UnhealthyDeployment(BaseModel):
    name: str
    namespace: str
    desired_replicas: int
    available_replicas: int
    unavailable_replicas: int
    conditions: list[str] = Field(default_factory=list)


class DeploymentInspection(BaseModel):
    healthy: bool
    unhealthy_deployments: list[UnhealthyDeployment] = Field(default_factory=list)
    total_deployments: int = 0
    error: str | None = None


class NetworkIssue(BaseModel):
    service: str
    namespace: str
    issue: str
    details: str


class NetworkInspection(BaseModel):
    issues: list[NetworkIssue] = Field(default_factory=list)
    error: str | None = None


class InvestigationPayload(BaseModel):
    pods: PodInspection
    logs: LogsInspection
    events: EventsInspection
    deployments: DeploymentInspection
    network: NetworkInspection


class InvestigateResponse(BaseModel):
    status: str
    investigation: InvestigationPayload
    diagnosis: Diagnosis

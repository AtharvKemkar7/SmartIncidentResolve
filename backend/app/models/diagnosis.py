from pydantic import BaseModel, Field


class Diagnosis(BaseModel):
    root_cause: str
    explanation: str
    fix: str
    kubectl_command: str
    prevention: str = ""
    confidence: int = Field(default=0, ge=0, le=100)
    confidence_reasoning: str = ""

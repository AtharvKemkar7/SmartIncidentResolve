from loguru import logger

from app.ai.analyzer import diagnosis_from_llm_payload, fallback_diagnosis
from app.ai.llm_client import LLMClientError, complete_json
from app.ai.prompts import build_messages
from app.models.diagnosis import Diagnosis
from app.models.investigation import InvestigationPayload


def diagnose_cluster(investigation: InvestigationPayload) -> Diagnosis:
    messages = build_messages(investigation)
    try:
        raw = complete_json(messages)
        diagnosis = diagnosis_from_llm_payload(raw, investigation)
        logger.info("AI diagnosis complete with confidence {}", diagnosis.confidence)
        return diagnosis
    except LLMClientError as exc:
        logger.error("AI diagnosis unavailable: {}", str(exc))
        return fallback_diagnosis(investigation, str(exc))


def suggest_fix(investigation: InvestigationPayload) -> str:
    return diagnose_cluster(investigation).fix

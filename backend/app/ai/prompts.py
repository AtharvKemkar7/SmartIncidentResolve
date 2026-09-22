import json

from app.models.investigation import InvestigationPayload

SYSTEM_PROMPT = """You are a Senior Kubernetes SRE.

Diagnose production incidents from structured cluster evidence.
Correlate pod status, logs, events, deployment health, and networking findings.
Do not blindly summarize. Identify the most likely root cause.

Rules:
- Be specific, practical, and Kubernetes-focused.
- Prefer evidence that is corroborated by more than one signal.
- If kubectl failed or evidence is missing, say so and lower confidence.
- Avoid vague advice such as "check the logs" without a concrete next step.
- Return ONLY valid JSON with these keys:
  root_cause: string
  explanation: string
  fix: string
  kubectl_command: string
  prevention: string
  confidence: integer from 0 to 100
  confidence_reasoning: string
- kubectl_command must contain real kubectl commands a beginner can run.
- Keep each string concise and actionable.
"""


def build_user_prompt(investigation: InvestigationPayload) -> str:
    evidence = investigation.model_dump()
    return (
        "Investigate this Kubernetes evidence and return JSON only.\n\n"
        "Pod Status:\n"
        f"{json.dumps(evidence['pods'], indent=2)}\n\n"
        "Logs:\n"
        f"{json.dumps(evidence['logs'], indent=2)}\n\n"
        "Events:\n"
        f"{json.dumps(evidence['events'], indent=2)}\n\n"
        "Deployment Health:\n"
        f"{json.dumps(evidence['deployments'], indent=2)}\n\n"
        "Networking Findings:\n"
        f"{json.dumps(evidence['network'], indent=2)}\n"
    )


def build_messages(investigation: InvestigationPayload) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(investigation)},
    ]

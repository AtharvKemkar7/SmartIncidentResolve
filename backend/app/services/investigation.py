from loguru import logger

from app.ai.agent import diagnose_cluster
from app.core.errors import friendly_kubectl_error
from app.kubernetes.deployments import inspect_deployments
from app.kubernetes.events import analyze_events
from app.kubernetes.kubectl import set_kubectl_context
from app.kubernetes.logs import collect_logs
from app.kubernetes.network import inspect_network
from app.kubernetes.pods import inspect_pods
from app.models.diagnosis import Diagnosis
from app.models.investigation import InvestigateResponse, InvestigationPayload
from app.services.history import record_investigation
from app.services.jobs import InvestigationJob


def run_investigation() -> InvestigationPayload:
    logger.info("Starting Kubernetes investigation")

    pods = inspect_pods()
    logs = collect_logs(pods.problematic_pods)
    events = analyze_events()
    deployments = inspect_deployments()
    network = inspect_network()

    logger.info("Kubernetes investigation complete")
    return InvestigationPayload(
        pods=pods,
        logs=logs,
        events=events,
        deployments=deployments,
        network=network,
    )


def run_investigation_with_diagnosis() -> tuple[InvestigationPayload, Diagnosis]:
    payload = run_investigation()
    diagnosis = diagnose_cluster(payload)
    return payload, diagnosis


def execute_investigation_job(job: InvestigationJob) -> None:
    set_kubectl_context(job.cluster)
    try:
        job.set_step("pods", "running")
        pods = inspect_pods()
        job.set_step("pods", "complete")

        job.set_step("logs", "running")
        logs = collect_logs(pods.problematic_pods)
        job.set_step("logs", "complete")

        job.set_step("events", "running")
        events = analyze_events()
        job.set_step("events", "complete")

        job.set_step("deployments", "running")
        deployments = inspect_deployments()
        job.set_step("deployments", "complete")

        job.set_step("network", "running")
        network = inspect_network()
        job.set_step("network", "complete")

        payload = InvestigationPayload(
            pods=pods,
            logs=logs,
            events=events,
            deployments=deployments,
            network=network,
        )

        job.set_step("ai", "running")
        diagnosis = diagnose_cluster(payload)
        job.set_step("ai", "complete")
        job.set_step("done", "complete")

        result = InvestigateResponse(
            status="success",
            investigation=payload,
            diagnosis=diagnosis,
        )
        record_investigation(job.cluster, payload, diagnosis, job.job_id)
        job.mark_complete(result)
    except Exception as exc:
        logger.exception("Investigation job failed")
        job.mark_failed(friendly_kubectl_error(str(exc)))
    finally:
        set_kubectl_context(None)

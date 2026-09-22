import json

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.security import CurrentUser
from app.kubernetes.kubectl import set_kubectl_context
from app.models.investigation import InvestigateResponse
from app.models.jobs import InvestigateRequest, JobStartResponse, JobStatusResponse
from app.services.history import record_investigation
from app.services.investigation import execute_investigation_job, run_investigation_with_diagnosis
from app.services.jobs import create_job, get_job, start_job

router = APIRouter()


@router.post("/investigate", response_model=InvestigateResponse)
def investigate(body: InvestigateRequest | None = None) -> InvestigateResponse:
    cluster = body.cluster if body else None
    set_kubectl_context(cluster)
    try:
        payload, diagnosis = run_investigation_with_diagnosis()
        record_investigation(cluster, payload, diagnosis)
        return InvestigateResponse(
            status="success",
            investigation=payload,
            diagnosis=diagnosis,
        )
    finally:
        set_kubectl_context(None)


@router.post("/investigate/jobs", response_model=JobStartResponse)
def start_investigation(body: InvestigateRequest, _user: CurrentUser) -> JobStartResponse:
    job = create_job(body.cluster)
    start_job(job, execute_investigation_job)
    snapshot = job.snapshot()
    return JobStartResponse(
        job_id=job.job_id,
        status=snapshot.status,
        cluster=snapshot.cluster,
        steps=snapshot.steps,
    )


@router.get("/investigate/jobs/{job_id}", response_model=JobStatusResponse)
def get_investigation_job(job_id: str, _user: CurrentUser) -> JobStatusResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation job not found")
    return job.snapshot()


@router.get("/investigate/jobs/{job_id}/events")
def stream_investigation_job(job_id: str, _user: CurrentUser) -> StreamingResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation job not found")

    def event_stream():
        version = -1
        while True:
            version = job.wait_for_change(version, timeout=1.0)
            snapshot = job.snapshot()
            yield f"data: {json.dumps(snapshot.model_dump())}\n\n"
            if snapshot.status in {"complete", "error"}:
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")

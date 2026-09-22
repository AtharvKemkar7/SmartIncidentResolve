import threading
from typing import Callable
from uuid import uuid4

from loguru import logger

from app.models.investigation import InvestigateResponse
from app.models.jobs import JobStep, JobStatusResponse


INVESTIGATION_STEPS = [
    ("pods", "Checking Pods"),
    ("logs", "Reading Logs"),
    ("events", "Analyzing Events"),
    ("deployments", "Inspecting Deployments"),
    ("network", "Checking Networking"),
    ("ai", "AI Reasoning"),
    ("done", "Root Cause Found"),
]


class InvestigationJob:
    def __init__(self, cluster: str | None) -> None:
        self.job_id = str(uuid4())
        self.cluster = cluster
        self.status = "queued"
        self.error: str | None = None
        self.result: InvestigateResponse | None = None
        self.steps = [JobStep(id=step_id, label=label, state="pending") for step_id, label in INVESTIGATION_STEPS]
        self._condition = threading.Condition()
        self._version = 0

    def snapshot(self) -> JobStatusResponse:
        return JobStatusResponse(
            job_id=self.job_id,
            status=self.status,
            cluster=self.cluster,
            steps=[step.model_copy() for step in self.steps],
            error=self.error,
            result=self.result,
        )

    def set_step(self, step_id: str, state: str) -> None:
        with self._condition:
            for step in self.steps:
                if step.id == step_id:
                    step.state = state
            self._bump()

    def mark_running(self) -> None:
        with self._condition:
            self.status = "running"
            self._bump()

    def mark_complete(self, result: InvestigateResponse) -> None:
        with self._condition:
            self.status = "complete"
            self.result = result
            self.error = None
            for step in self.steps:
                if step.state != "complete":
                    step.state = "complete"
            self._bump()

    def mark_failed(self, error: str) -> None:
        with self._condition:
            self.status = "error"
            self.error = error
            self._bump()

    def wait_for_change(self, version: int, timeout: float = 1.0) -> int:
        with self._condition:
            if self._version != version:
                return self._version
            self._condition.wait(timeout=timeout)
            return self._version

    def current_version(self) -> int:
        with self._condition:
            return self._version

    def _bump(self) -> None:
        self._version += 1
        self._condition.notify_all()


_jobs: dict[str, InvestigationJob] = {}
_lock = threading.Lock()


def get_job(job_id: str) -> InvestigationJob | None:
    with _lock:
        return _jobs.get(job_id)


def create_job(cluster: str | None) -> InvestigationJob:
    job = InvestigationJob(cluster)
    with _lock:
        _jobs[job.job_id] = job
    return job


def start_job(job: InvestigationJob, worker: Callable[[InvestigationJob], None]) -> None:
    thread = threading.Thread(target=_run, args=(job, worker), daemon=True)
    thread.start()


def _run(job: InvestigationJob, worker: Callable[[InvestigationJob], None]) -> None:
    try:
        job.mark_running()
        worker(job)
    except Exception as exc:
        logger.exception("Investigation job failed")
        job.mark_failed(str(exc))

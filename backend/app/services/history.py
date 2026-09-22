import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from loguru import logger

from app.core.config import settings
from app.models.diagnosis import Diagnosis
from app.models.history import HistoryItem
from app.models.investigation import InvestigationPayload

_history_lock = threading.Lock()


def _history_path() -> Path:
    directory = Path(settings.data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "investigations.json"


def _load_history_unlocked() -> list[HistoryItem]:
    path = _history_path()
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read investigation history: {}", exc)
        return []
    items: list[HistoryItem] = []
    for entry in raw:
        try:
            items.append(HistoryItem.model_validate(entry))
        except Exception:
            continue
    return items


def load_history() -> list[HistoryItem]:
    with _history_lock:
        return _load_history_unlocked()


def save_history(items: list[HistoryItem]) -> None:
    path = _history_path()
    payload = [item.model_dump() for item in items[:50]]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _primary_namespace(investigation: InvestigationPayload) -> str:
    if investigation.pods.problematic_pods:
        return investigation.pods.problematic_pods[0].namespace
    if investigation.deployments.unhealthy_deployments:
        return investigation.deployments.unhealthy_deployments[0].namespace
    if investigation.network.issues:
        return investigation.network.issues[0].namespace
    return "default"


def _status_label(investigation: InvestigationPayload, diagnosis: Diagnosis) -> str:
    if investigation.pods.error or investigation.events.error:
        return "error"
    if investigation.pods.healthy and investigation.deployments.healthy and not investigation.network.issues:
        return "healthy"
    return "diagnosed"


def record_investigation(
    cluster: str | None,
    investigation: InvestigationPayload,
    diagnosis: Diagnosis,
    job_id: str | None = None,
) -> HistoryItem:
    item = HistoryItem(
        id=str(uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        cluster=cluster or "default",
        namespace=_primary_namespace(investigation),
        root_cause=diagnosis.root_cause,
        confidence=diagnosis.confidence,
        status=_status_label(investigation, diagnosis),
        job_id=job_id,
    )
    with _history_lock:
        items = [item, *_load_history_unlocked()]
        save_history(items)
    return item

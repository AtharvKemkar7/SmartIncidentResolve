import os
import subprocess
import threading
from dataclasses import dataclass

from loguru import logger

from app.core.config import settings

KUBECTL_BIN = "kubectl"
_thread_state = threading.local()


def set_kubectl_context(context: str | None) -> None:
    _thread_state.context = context


def get_kubectl_context() -> str | None:
    return getattr(_thread_state, "context", None)


@dataclass
class KubectlResult:
    success: bool
    args: list[str]
    stdout: str
    stderr: str
    return_code: int
    error: str | None = None


def run_kubectl(
    *args: str,
    timeout: int | None = None,
) -> KubectlResult:
    context = get_kubectl_context()
    extra: list[str] = ["--context", context] if context else []
    command = [KUBECTL_BIN, *extra, *args]
    env = os.environ.copy()

    if settings.kubeconfig_path:
        env["KUBECONFIG"] = settings.kubeconfig_path

    timeout_seconds = timeout or settings.kubectl_timeout_seconds
    logger.info("Running kubectl: {}", " ".join(command))

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
            check=False,
        )
    except FileNotFoundError:
        message = "kubectl is not installed or not on PATH"
        logger.error(message)
        return KubectlResult(
            success=False,
            args=list(args),
            stdout="",
            stderr=message,
            return_code=127,
            error=message,
        )
    except subprocess.TimeoutExpired:
        message = f"kubectl timed out after {timeout_seconds}s"
        logger.error("{}: {}", message, " ".join(command))
        return KubectlResult(
            success=False,
            args=list(args),
            stdout="",
            stderr=message,
            return_code=124,
            error=message,
        )
    except OSError as exc:
        message = f"failed to execute kubectl: {exc}"
        logger.error(message)
        return KubectlResult(
            success=False,
            args=list(args),
            stdout="",
            stderr=str(exc),
            return_code=1,
            error=message,
        )

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    success = completed.returncode == 0

    if success:
        logger.debug("kubectl succeeded: {}", " ".join(command))
    else:
        logger.warning(
            "kubectl failed (code {}): {} | {}",
            completed.returncode,
            " ".join(command),
            stderr.strip() or stdout.strip(),
        )

    return KubectlResult(
        success=success,
        args=list(args),
        stdout=stdout,
        stderr=stderr,
        return_code=completed.returncode,
        error=None if success else (stderr.strip() or stdout.strip() or "kubectl command failed"),
    )

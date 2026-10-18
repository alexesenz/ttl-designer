import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from fastapi import FastAPI

from .api.routes import router


def _version() -> str:
    try:
        return version("ttl-designer")
    except PackageNotFoundError:
        return "unknown"


def _git_commit() -> str:
    """Commit desplegado, para confirmar en /health que un reinicio tomó el código nuevo."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return out.stdout.strip() or "unknown"


VERSION = _version()
GIT_COMMIT = _git_commit()

app = FastAPI(title="TTL Designer", version=VERSION)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION, "commit": GIT_COMMIT}

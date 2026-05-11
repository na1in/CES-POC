"""
Local filesystem document storage (PoC).

Set UPLOAD_DIR env var to override the default ./uploads directory.
Swap this module for an S3-compatible implementation before production.
"""
import os
import uuid
from pathlib import Path

_UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "./uploads"))

_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


async def save(payment_id: str, filename: str, data: bytes) -> str:
    """Write bytes to disk; return storage_path relative to UPLOAD_DIR."""
    dest_dir = _UPLOAD_DIR / payment_id
    _ensure_dir(dest_dir)
    safe_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
    (dest_dir / safe_name).write_bytes(data)
    return str(Path(payment_id) / safe_name)


def full_path(storage_path: str) -> Path:
    """Resolve storage_path to an absolute filesystem path."""
    return (_UPLOAD_DIR / storage_path).resolve()


async def delete(storage_path: str) -> None:
    """Remove file from disk (DB soft-delete is the authoritative record)."""
    p = full_path(storage_path)
    if p.exists():
        p.unlink()

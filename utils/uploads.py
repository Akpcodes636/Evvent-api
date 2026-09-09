from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from core.exceptions import AppError

UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploads"
IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
VIDEO_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


async def save_upload(file: UploadFile, *, subdir: str, allowed_types: set[str]) -> str:
    if file.content_type not in allowed_types:
        raise AppError(f"Unsupported file type: {file.content_type}", status_code=400)

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise AppError("File is too large", status_code=400)

    extension = Path(file.filename or "").suffix
    filename = f"{uuid4().hex}{extension}"
    destination_dir = UPLOAD_ROOT / subdir
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / filename
    destination.write_bytes(contents)

    return f"/uploads/{subdir}/{filename}"

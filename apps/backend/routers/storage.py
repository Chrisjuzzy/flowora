from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import uuid

from database_production import get_db
from security import get_current_user
from services.object_storage import ObjectStorageService

router = APIRouter(prefix="/storage", tags=["storage"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    storage = ObjectStorageService()
    content = await file.read()
    object_name = f"{current_user.id}/{uuid.uuid4().hex}-{file.filename}"
    try:
        storage.upload_bytes(object_name, content, content_type=file.content_type)
        return {"status": "uploaded", "object_name": object_name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/download/{object_name:path}")
def download_file(
    object_name: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    storage = ObjectStorageService()
    try:
        obj = storage.download(object_name)
        return StreamingResponse(obj, media_type="application/octet-stream")
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))

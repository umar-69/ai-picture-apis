from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.dependencies import get_supabase, get_current_user
from app.config import GCS_BUCKET_NAME
from supabase import Client

router = APIRouter(prefix="/storage", tags=["Storage"])

BUCKET_NAME = GCS_BUCKET_NAME or "ai-driving-lessons"

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    try:
        file_content = await file.read()
        file_path = f"{current_user.id}/{file.filename}"
        
        # Upload file to Supabase Storage
        res = supabase.storage.from_(BUCKET_NAME).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": file.content_type}
        )
        
        # Get public URL
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_path)
        
        return {"file_path": file_path, "public_url": public_url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/list")
def list_files(
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    try:
        res = supabase.storage.from_(BUCKET_NAME).list(path=f"{current_user.id}")
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

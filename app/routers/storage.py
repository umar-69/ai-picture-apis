from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from typing import List
from app.dependencies import get_supabase, get_current_user, get_current_user_optional, get_supabase_admin
from app.config import GCS_BUCKET_NAME
from supabase import Client
import uuid

router = APIRouter(prefix="/storage", tags=["Storage"])

BUCKET_NAME = "dataset-images"  # Use the same bucket as the analyze endpoint

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    dataset_id: str = Form(None),
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase_admin)
):
    """
    Upload a single file to Supabase Storage.
    Supports anonymous uploads for free tier.
    """
    try:
        file_content = await file.read()
        
        # Use dataset_id if provided, otherwise create a temp folder
        folder = dataset_id if dataset_id else "temp"
        
        # Generate unique filename
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        file_path = f"{folder}/{uuid.uuid4()}.{file_ext}"
        
        # Upload file to Supabase Storage
        supabase.storage.from_(BUCKET_NAME).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": file.content_type}
        )
        
        # Get public URL
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_path)
        
        return {"file_path": file_path, "public_url": public_url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/upload-multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    dataset_id: str = Form(None),
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase_admin)
):
    """
    Upload multiple files to Supabase Storage.
    Supports anonymous uploads for free tier.
    Returns list of public URLs.
    """
    try:
        uploaded_files = []
        folder = dataset_id if dataset_id else "temp"
        
        for file in files:
            file_content = await file.read()
            
            # Generate unique filename
            file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
            file_path = f"{folder}/{uuid.uuid4()}.{file_ext}"
            
            # Upload file to Supabase Storage
            supabase.storage.from_(BUCKET_NAME).upload(
                path=file_path,
                file=file_content,
                file_options={"content-type": file.content_type}
            )
            
            # Get public URL
            public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_path)
            
            uploaded_files.append({
                "file_path": file_path,
                "public_url": public_url,
                "filename": file.filename
            })
        
        return {"files": uploaded_files, "count": len(uploaded_files)}
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

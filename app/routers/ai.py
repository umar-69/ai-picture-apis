import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List
import uuid
import json
from app.schemas import GenerateImageRequest, AnalyzeImageRequest
from app.dependencies import get_current_user, get_current_user_optional, get_supabase
from app.config import GOOGLE_API_KEY
from supabase import Client
import os

# Configure Gemini
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/generate")
async def generate_image(
    request: GenerateImageRequest,
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase)
):
    # This is a placeholder for actual Gemini Image Generation
    # Gemini Pro Vision is text/image-to-text. 
    # For Image Generation, we might need Imagen or a specific Gemini capability if available.
    # Assuming "gemini-3-pro-image-preview" is the model user mentioned.
    
    try:
        # 1. Fetch Business Profile context if needed (only if user is logged in)
        business_context = ""
        if current_user:
            try:
                profile_res = supabase.table("business_profiles").select("*").eq("id", current_user.id).single().execute()
                if profile_res.data:
                    p = profile_res.data
                    business_context = f"Brand: {p.get('business_name')}. Vibe: {p.get('vibes')}. Theme: {p.get('theme')}."
            except Exception:
                # Ignore if profile not found or other error for optional user
                pass

        # 2. Fetch Dataset context if provided
        dataset_context = ""
        if request.dataset_id:
            try:
                 dataset_res = supabase.table("datasets").select("*").eq("id", request.dataset_id).single().execute()
                 if dataset_res.data:
                     dataset_context = f"Style Guidelines: {dataset_res.data.get('master_prompt')}"
            except Exception:
                # Ignore if dataset not found (PGRST116) or other error.
                # This allows anonymous users with local-only dataset IDs to still generate images.
                pass

        full_prompt = f"{business_context} {dataset_context} {request.prompt}"
        
        # Placeholder for actual generation call
        # model = genai.GenerativeModel('gemini-3-pro-image-preview') # Hypothetical model name
        # response = model.generate_content(full_prompt)
        
        # Mock response for now as we don't have the exact model capability in this env
        # In a real scenario, you'd get the image, upload to Supabase 'generated-images', and return URL.
        
        return {"message": "Image generation initiated", "prompt_used": full_prompt}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/dataset/analyze")
async def analyze_dataset_images(
    dataset_id: str = Form(None),
    datasetId: str = Form(None), # Alias for frontend convenience
    files: List[UploadFile] = File(None),
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase)
):
    """
    Uploads images to Supabase Storage, analyzes them, and saves results to DB.
    Allows anonymous users for free tries (frontend managed limit).
    """
    # Handle optional/aliased inputs
    actual_dataset_id = dataset_id or datasetId
    if not actual_dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required")
    
    if not files:
         raise HTTPException(status_code=400, detail="No files provided. Please upload at least one image.")

    # If current_user is None, it's an anonymous request.
    # We allow it for free tries.
    
    results = []
    
    for file in files:
        try:
            # 1. Upload to Supabase Storage
            file_content = await file.read()
            file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
            file_path = f"{actual_dataset_id}/{uuid.uuid4()}.{file_ext}"
            
            # Upload file
            # Note: Supabase Python client might raise error if upload fails
            supabase.storage.from_("dataset-images").upload(
                path=file_path,
                file=file_content,
                file_options={"content-type": file.content_type}
            )
            
            # Get Public URL
            # The method returns the URL string directly in recent versions
            public_url = supabase.storage.from_("dataset-images").get_public_url(file_path)
            
            # 2. Analyze with Gemini
            # We use the file content we already have in memory for efficiency.
            
            analysis_result = {}
            if GOOGLE_API_KEY:
                try:
                    # Use gemini-3-flash for state-of-the-art vision analysis
                    model = genai.GenerativeModel('gemini-3-flash')
                    
                    # Prepare the image part
                    image_part = {
                        "mime_type": file.content_type or "image/jpeg",
                        "data": file_content
                    }
                    
                    prompt = """
                    Analyze this image and provide a JSON output with the following keys:
                    - "description": A detailed description of the image content and style.
                    - "tags": A list of 5-10 keywords describing the style, subject, and vibe.
                    - "lighting": Description of the lighting (e.g., natural, studio, dark, bright).
                    - "colors": Dominant colors or color palette.
                    - "vibe": The overall mood or atmosphere.
                    
                    Ensure the output is valid JSON. Do not include markdown formatting like ```json.
                    """
                    
                    response = model.generate_content([prompt, image_part])
                    
                    # Parse the response
                    response_text = response.text.strip()
                    # Clean up markdown code blocks if present
                    if response_text.startswith("```json"):
                        response_text = response_text[7:]
                    if response_text.startswith("```"):
                        response_text = response_text[3:]
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]
                        
                    try:
                        analysis_result = json.loads(response_text)
                    except json.JSONDecodeError:
                        # Fallback if JSON parsing fails
                        analysis_result = {
                            "description": response_text,
                            "tags": [],
                            "error": "Failed to parse structured analysis"
                        }
                        
                except Exception as ai_error:
                    print(f"AI Analysis failed: {ai_error}")
                    analysis_result = {"error": f"AI analysis failed: {str(ai_error)}"}
            
            # 3. Store in DB
            data = {
                "dataset_id": actual_dataset_id,
                "image_url": public_url,
                "analysis_result": analysis_result
            }
            
            # Insert and return the created row
            res = supabase.table("dataset_images").insert(data).execute()
            if res.data:
                results.append(res.data[0])
                
        except Exception as e:
            print(f"Error processing file {file.filename}: {e}")
            # We continue processing other files even if one fails
            continue

    return {"results": results}

@router.get("/dataset/{dataset_id}/images")
async def get_dataset_images(
    dataset_id: str,
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase)
):
    """
    Fetch all images and their analysis results for a specific dataset.
    """
    try:
        # Fetch images from the database
        res = supabase.table("dataset_images").select("*").eq("dataset_id", dataset_id).execute()
        
        if not res.data:
            return {"images": []}
            
        return {"images": res.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/analyze")
async def analyze_style(
    request: AnalyzeImageRequest,
    current_user = Depends(get_current_user),
):
    try:
        model = genai.GenerativeModel('gemini-pro-vision')
        
        # In reality, we'd need to download the images from URLs and pass them to the model
        # prompt = "Analyze these images and extract a master style prompt including lighting, colors, and vibe."
        
        return {"message": "Analysis endpoint ready (requires image download logic)"}
    except Exception as e:
         raise HTTPException(status_code=400, detail=str(e))

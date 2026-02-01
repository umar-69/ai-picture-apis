from google import genai
from google.genai import types
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List
import uuid
import json
import base64
import requests
import io
from PIL import Image as PILImage
from app.schemas import GenerateImageRequest, AnalyzeImageRequest, AnalyzeDatasetRequest
from app.dependencies import get_current_user, get_current_user_optional, get_supabase, get_supabase_admin
from app.config import GOOGLE_API_KEY
from supabase import Client
import os

# Configure Gemini Client
client = None
if GOOGLE_API_KEY:
    client = genai.Client(api_key=GOOGLE_API_KEY)

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/generate")
async def generate_image(
    request: GenerateImageRequest,
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase_admin)
):
    """
    Generate an image using Nano Banana Pro (Gemini 3 Pro Image Preview).
    Professional asset production with advanced reasoning and high-resolution output.
    Supports: 1K/2K/4K resolution, up to 14 reference images, business profile context.
    Returns the generated image URL from Supabase storage.
    """
    
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google API key not configured")
    
    try:
        # 1. Fetch Business Profile context if needed (only if user is logged in)
        business_context = ""
        if current_user:
            try:
                profile_res = supabase.table("business_profiles").select("*").eq("id", current_user.id).single().execute()
                if profile_res.data:
                    p = profile_res.data
                    business_context = f"Brand: {p.get('business_name')}. Vibe: {p.get('vibes')}. Theme: {p.get('theme')}. "
            except Exception:
                # Ignore if profile not found or other error for optional user
                pass

        # 2. Fetch Dataset context if provided (including actual images as visual reference)
        dataset_context = ""
        dataset_master_prompt = ""
        reference_images = []
        
        if request.dataset_id:
            try:
                # Fetch dataset and its analyzed images for style reference
                dataset_res = supabase.table("datasets").select("*").eq("id", request.dataset_id).single().execute()
                if dataset_res.data:
                    dataset_master_prompt = dataset_res.data.get('master_prompt', '')
                    if dataset_master_prompt:
                        dataset_context = f"Style Guidelines: {dataset_master_prompt}. "
                    
                    # Fetch actual images from dataset to use as visual reference
                    # Nano Banana supports up to 14 reference images (up to 6 objects, up to 5 people)
                    images_res = supabase.table("dataset_images").select("image_url, analysis_result").eq("dataset_id", request.dataset_id).limit(5).execute()
                    
                    if images_res.data:
                        # Extract style information from analyzed images for text context
                        style_tags = []
                        for img in images_res.data:
                            if img.get('analysis_result'):
                                analysis = img['analysis_result']
                                if 'vibe' in analysis:
                                    style_tags.append(analysis['vibe'])
                                if 'lighting' in analysis:
                                    style_tags.append(analysis['lighting'])
                            
                            # Download the actual image to use as visual reference
                            if img.get('image_url'):
                                try:
                                    # Download image from Supabase storage
                                    img_response = requests.get(img['image_url'], timeout=10)
                                    if img_response.status_code == 200:
                                        # Convert to PIL Image for Gemini
                                        pil_image = PILImage.open(io.BytesIO(img_response.content))
                                        reference_images.append(pil_image)
                                        print(f"Added reference image: {img['image_url']}")
                                except Exception as img_error:
                                    print(f"Warning: Could not load reference image {img.get('image_url')}: {img_error}")
                                    # Continue with other images
                        
                        if style_tags:
                            dataset_context += f"Reference style: {', '.join(set(style_tags))}. "
                        
                        if reference_images:
                            dataset_context += f"Match the style and aesthetic of the {len(reference_images)} reference image(s) provided. "
                            
            except Exception as e:
                print(f"Warning: Could not fetch dataset context: {e}")
                # Continue anyway - dataset context is optional

        # 3. Build the full prompt with context
        style_suffix = ""
        if request.style:
            style_suffix = f" Style: {request.style}."
        
        full_prompt = f"{business_context}{dataset_context}{request.prompt}{style_suffix}".strip()
        
        print(f"Generating image with Nano Banana Pro (Gemini 3). Prompt: {full_prompt}")
        if reference_images:
            print(f"Using {len(reference_images)} reference images from dataset")
        
        # 4. Generate image using Nano Banana Pro (Gemini 3 Pro Image Preview)
        if not client:
             raise HTTPException(status_code=500, detail="Gemini client not initialized")

        # Map aspect ratio from request format (e.g., "1:1") to API format
        aspect_ratio_map = {
            "1:1": "1:1",
            "16:9": "16:9",
            "9:16": "9:16",
            "4:3": "4:3",
            "3:4": "3:4",
            "2:3": "2:3",
            "3:2": "3:2",
            "4:5": "4:5",
            "5:4": "5:4",
            "21:9": "21:9"
        }
        aspect_ratio = aspect_ratio_map.get(request.aspect_ratio, "1:1")
        resolution = "2K"
        
        # Build parts list with prompt and reference images
        parts = [types.Part.from_text(text=full_prompt)]
        
        # Add reference images (if any)
        for ref_img in reference_images:
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            ref_img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            img_bytes = img_byte_arr.read()
            
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
            
        contents = [types.Content(role="user", parts=parts)]
        
        # Generate the image
        response = client.models.generate_content(
            model='gemini-3-pro-image-preview',
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=resolution
                )
            )
        )
        
        # 5. Extract the generated image from response
        image_bytes = None
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    break
        
        if not image_bytes:
            raise HTTPException(status_code=500, detail="No image generated by Nano Banana")
        
        # 6. Upload to Supabase Storage
        file_ext = request.format or "png"
        file_name = f"generated-{uuid.uuid4()}.{file_ext}"
        file_path = f"generated/{file_name}"
        
        # Upload to 'generated-images' bucket (create if doesn't exist)
        try:
            supabase.storage.from_("generated-images").upload(
                path=file_path,
                file=image_bytes,
                file_options={"content-type": f"image/{file_ext}"}
            )
        except Exception as upload_error:
            # If bucket doesn't exist, try to create it
            print(f"Upload error: {upload_error}")
            # For now, just re-raise - bucket should be created manually in Supabase dashboard
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to upload image to storage. Please ensure 'generated-images' bucket exists in Supabase. Error: {str(upload_error)}"
            )
        
        # 7. Get public URL
        public_url = supabase.storage.from_("generated-images").get_public_url(file_path)
        
        # 8. Optionally save generation record to database
        if current_user:
            try:
                generation_record = {
                    "user_id": current_user.id,
                    "prompt": request.prompt,
                    "full_prompt": full_prompt,
                    "image_url": public_url,
                    "dataset_id": request.dataset_id,
                    "style": request.style,
                    "aspect_ratio": request.aspect_ratio
                }
                # Note: You may want to create a 'generated_images' table to track this
                # supabase.table("generated_images").insert(generation_record).execute()
            except Exception as db_error:
                print(f"Warning: Could not save generation record: {db_error}")
                # Continue anyway - the image was generated successfully
        
        # 9. Return the image URL (this is what the frontend expects!)
        return {
            "image_url": public_url,
            "caption": request.prompt,
            "prompt_used": full_prompt,
            "dataset_id": request.dataset_id,
            "style": request.style,
            "aspect_ratio": request.aspect_ratio
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Image generation error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

@router.post("/dataset/analyze")
async def analyze_dataset_images(
    dataset_id: str = Form(None),
    datasetId: str = Form(None), # Alias for frontend convenience
    files: List[UploadFile] = File(None),
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase_admin)
):
    """
    Uploads images to Supabase Storage, analyzes them, and saves results to DB.
    Allows anonymous users for free tries (frontend managed limit).
    Uses Service Role (admin) to bypass RLS for uploads/inserts.
    """
    # Handle optional/aliased inputs
    actual_dataset_id = dataset_id or datasetId
    if not actual_dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required")
    
    # Ensure dataset exists to satisfy FK constraint
    try:
        # Check if dataset exists
        ds_check = supabase.table("datasets").select("id").eq("id", actual_dataset_id).execute()
        if not ds_check.data:
            # Create it if missing
            # user_id is now nullable to support anonymous uploads
            new_dataset = {
                "id": actual_dataset_id,
                "user_id": current_user.id if current_user else None,
                "name": "Untitled Dataset"
            }
            supabase.table("datasets").insert(new_dataset).execute()
            print(f"Created missing dataset: {actual_dataset_id} for {'user ' + current_user.id if current_user else 'anonymous user'}")
    except Exception as e:
        print(f"Warning: Could not check/create dataset: {e}")
        # Continue anyway - if dataset creation fails, the image insert will fail with FK error

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
            if GOOGLE_API_KEY and client:
                try:
                    # Use gemini-3-flash-preview for state-of-the-art vision analysis with code execution
                    # We enable code_execution to allow the model to run code for better reasoning (Agentic Vision)
                    
                    prompt = """
                    Analyze this image and provide a JSON output with the following keys:
                    - "description": A detailed description of the image content and style.
                    - "tags": A list of 5-10 keywords describing the style, subject, and vibe.
                    - "lighting": Description of the lighting (e.g., natural, studio, dark, bright).
                    - "colors": Dominant colors or color palette.
                    - "vibe": The overall mood or atmosphere.
                    
                    You can use code execution to inspect the image details if needed (e.g. counting objects, checking pixel distributions), 
                    but the final output must be the JSON structure above.
                    
                    Ensure the output is valid JSON. Do not include markdown formatting like ```json.
                    """
                    
                    parts = [
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=file_content, mime_type=file.content_type or "image/jpeg")
                    ]
                    
                    response = client.models.generate_content(
                        model='gemini-3-flash-preview',
                        contents=[types.Content(role="user", parts=parts)],
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(code_execution=types.ToolCodeExecution())]
                        )
                    )
                    
                    # Parse the response
                    # With code execution, the response might contain multiple parts. 
                    # We need to extract the text part.
                    response_text = response.text.strip() if response.text else ""
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

@router.post("/dataset/analyze-fast")
async def analyze_dataset_images_fast(
    request: AnalyzeDatasetRequest,
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase_admin)
):
    """
    Fast parallel analysis of images using Gemini 3.0 Flash.
    Accepts a list of image URLs (already in storage) and analyzes them.
    Optimized for large quantities of images with the full detailed prompt.
    """
    # Ensure dataset exists
    try:
        ds_check = supabase.table("datasets").select("id").eq("id", request.dataset_id).execute()
        if not ds_check.data:
            new_dataset = {
                "id": request.dataset_id,
                "user_id": current_user.id if current_user else None,
                "name": "Untitled Dataset"
            }
            supabase.table("datasets").insert(new_dataset).execute()
    except Exception as e:
        print(f"Warning: Could not check/create dataset: {e}")

    if not request.image_urls:
         raise HTTPException(status_code=400, detail="No image URLs provided.")

    import asyncio
    import httpx

    async def process_single_image(image_url):
        try:
            # 1. Download image content
            async with httpx.AsyncClient() as http_client:
                resp = await http_client.get(image_url)
                if resp.status_code != 200:
                    return {"error": f"Failed to download image: {resp.status_code}", "image_url": image_url}
                file_content = resp.content
                content_type = resp.headers.get("content-type", "image/jpeg")

            # 2. Analyze with Gemini 3.0 Flash
            analysis_result = {}
            if GOOGLE_API_KEY and client:
                try:
                    prompt = """
                    Analyze this image and provide a JSON output with the following keys:
                    - "description": A detailed description of the image content and style.
                    - "tags": A list of 5-10 keywords describing the style, subject, and vibe.
                    - "lighting": Description of the lighting (e.g., natural, studio, dark, bright).
                    - "colors": Dominant colors or color palette.
                    - "vibe": The overall mood or atmosphere.
                    
                    You can use code execution to inspect the image details if needed.
                    Ensure the output is valid JSON. Do not include markdown formatting.
                    """
                    
                    parts = [
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=file_content, mime_type=content_type)
                    ]
                    
                    # Using gemini-3-flash-preview for maximum speed and intelligence
                    response = client.models.generate_content(
                        model='gemini-3-flash-preview',
                        contents=[types.Content(role="user", parts=parts)],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    
                    analysis_result = json.loads(response.text)
                        
                except Exception as ai_error:
                    print(f"AI Analysis failed for {image_url}: {ai_error}")
                    analysis_result = {"error": str(ai_error)}
            
            # 3. Store in DB
            data = {
                "dataset_id": request.dataset_id,
                "image_url": image_url,
                "analysis_result": analysis_result
            }
            
            res = supabase.table("dataset_images").insert(data).execute()
            return res.data[0] if res.data else None
                
        except Exception as e:
            print(f"Error processing url {image_url}: {e}")
            return {"error": str(e), "image_url": image_url}

    # Process all images in parallel
    # Limit concurrency to avoid hitting rate limits or overwhelming the server
    semaphore = asyncio.Semaphore(10) # Process 10 images at a time
    
    async def sem_process(url):
        async with semaphore:
            return await process_single_image(url)

    results = await asyncio.gather(*[sem_process(url) for url in request.image_urls])
    
    # Filter out None results
    valid_results = [r for r in results if r and "error" not in r]
    
    return {"results": valid_results, "total_processed": len(request.image_urls), "successful": len(valid_results)}

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
        # In reality, we'd need to download the images from URLs and pass them to the model
        # prompt = "Analyze these images and extract a master style prompt including lighting, colors, and vibe."
        
        return {"message": "Analysis endpoint ready (requires image download logic)"}
    except Exception as e:
         raise HTTPException(status_code=400, detail=str(e))

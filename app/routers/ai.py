from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List
import uuid
import json
import base64
import requests
import io
import time
import asyncio
import tempfile
from PIL import Image as PILImage
from app.schemas import GenerateImageRequest, AnalyzeImageRequest, AnalyzeDatasetRequest, UpdateDatasetTrainingStatusRequest
from app.dependencies import get_current_user, get_current_user_optional, get_supabase, get_supabase_admin
from app.config import GOOGLE_API_KEY
from supabase import Client
import os

# ─── Constants ────────────────────────────────────────────────────
MAX_REFERENCE_IMAGES = 5          # Cap reference images to reduce payload
MAX_IMAGE_DIMENSION = 1024        # Resize large images to this max width/height
GEMINI_MAX_RETRIES = 3            # Retry transient 500 errors up to 3 times
GEMINI_RETRY_BASE_DELAY = 2      # Base delay in seconds (exponential backoff)


def _build_image_search_text(analysis: dict) -> str:
    """
    Build a rich text representation of an image's analysis for embedding.
    
    Combines all analyzed fields into a single string that captures the
    full visual identity of the image — tags, description, key elements,
    theme, style, vibe, colors, and lighting. This text is what gets
    embedded and compared against the user's prompt.
    """
    if not analysis:
        return ""
    
    parts = []
    
    # Tags — most specific visual identifiers (listed first for emphasis)
    tags = analysis.get('tags', [])
    if isinstance(tags, list) and tags:
        parts.append(f"Tags: {', '.join(tags)}")
    
    # Key elements — specific design features
    key_elements = analysis.get('key_elements', [])
    if isinstance(key_elements, list) and key_elements:
        parts.append(f"Key elements: {', '.join(key_elements)}")
    
    # Theme and style
    theme = analysis.get('theme', '')
    if theme:
        parts.append(f"Theme: {theme}")
    
    image_style = analysis.get('image_style', '')
    if image_style:
        parts.append(f"Style: {image_style}")
    
    # Vibe / mood
    vibe = analysis.get('vibe', '')
    if vibe:
        parts.append(f"Mood: {vibe}")
    
    # Colors
    colors = analysis.get('colors', '')
    if isinstance(colors, list):
        colors = ', '.join(colors)
    if colors:
        parts.append(f"Colors: {colors}")
    
    # Lighting
    lighting = analysis.get('lighting', '')
    if lighting:
        parts.append(f"Lighting: {lighting}")
    
    # Description — rich scene context (last, as it's the longest)
    description = analysis.get('description', '')
    if description:
        parts.append(f"Description: {description}")
    
    return ". ".join(parts)


def _cosine_similarity(vec_a: list, vec_b: list) -> float:
    """Compute cosine similarity between two vectors. Returns -1 to 1."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = sum(a * a for a in vec_a) ** 0.5
    mag_b = sum(b * b for b in vec_b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _find_relevant_images_semantic(
    gemini_client,
    prompt: str,
    images_data: list,
    max_images: int = MAX_REFERENCE_IMAGES,
) -> list:
    """
    Use Gemini Embedding API to find the most semantically relevant
    dataset images for the user's prompt.
    
    How it works:
      1. Build a search text for each image from its analysis_result
         (tags, description, key_elements, theme, style, vibe, colors, lighting).
      2. Send ONE batch embed_content call with [prompt, img1_text, img2_text, ...]
         to Gemini's embedding model.
      3. Compute cosine similarity between the prompt embedding and each image embedding.
      4. Return the top N images ranked by similarity.
    
    Falls back to returning the first N images if embedding fails.
    """
    # Build search text for each image
    image_texts = []
    valid_images = []  # track which images have usable analysis text
    
    for img in images_data:
        analysis = img.get('analysis_result', {})
        search_text = _build_image_search_text(analysis)
        if search_text:
            image_texts.append(search_text)
            valid_images.append(img)
    
    if not valid_images:
        print("No analyzed images found — using first images as fallback")
        return images_data[:max_images]
    
    try:
        # ONE API call: embed the prompt + all image texts together
        # First item = prompt, rest = image analysis texts
        all_texts = [prompt] + image_texts
        
        print(f"Embedding {len(all_texts)} texts (1 prompt + {len(image_texts)} images) via Gemini...")
        
        embed_result = gemini_client.models.embed_content(
            model="gemini-embedding-001",
            contents=all_texts,
            config=types.EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY",
            ),
        )
        
        # Extract embeddings: first one is the prompt, rest are images
        prompt_embedding = embed_result.embeddings[0].values
        image_embeddings = embed_result.embeddings[1:]
        
        # Score each image by cosine similarity to the prompt
        scored = []
        for i, img_embedding in enumerate(image_embeddings):
            similarity = _cosine_similarity(prompt_embedding, img_embedding.values)
            scored.append((similarity, valid_images[i]))
        
        # Sort by similarity descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Select top N
        selected = scored[:max_images]
        
        print(f"Semantic relevance ranking — top {len(selected)} of {len(valid_images)} images:")
        for rank, (sim, img) in enumerate(selected, 1):
            url = img.get('image_url', 'N/A')
            short_url = url.split('/')[-1] if url else 'N/A'
            # Show a few top tags for context
            tags = img.get('analysis_result', {}).get('tags', [])
            top_tags = ', '.join(tags[:4]) if tags else 'no tags'
            print(f"  #{rank}: similarity={sim:.4f}  [{top_tags}]  {short_url}")
        
        return [img for _, img in selected]
        
    except Exception as e:
        # If embedding fails (API error, quota, etc.), fall back to first N
        print(f"Warning: Semantic search failed ({e}), falling back to first {max_images} images")
        return images_data[:max_images]


def _resize_image_if_needed(pil_image: PILImage.Image, max_dim: int = MAX_IMAGE_DIMENSION) -> PILImage.Image:
    """Resize image if either dimension exceeds max_dim, preserving aspect ratio."""
    w, h = pil_image.size
    if w <= max_dim and h <= max_dim:
        return pil_image
    
    if w > h:
        new_w = max_dim
        new_h = int(h * (max_dim / w))
    else:
        new_h = max_dim
        new_w = int(w * (max_dim / h))
    
    return pil_image.resize((new_w, new_h), PILImage.LANCZOS)


def _ensure_rgb_image(pil_image: PILImage.Image) -> PILImage.Image:
    """
    Ensure image is in RGB mode for Gemini API compatibility.
    Some JPEGs/PNGs have RGBA, P (palette), or LA mode which can cause
    400 INVALID_ARGUMENT when sent to generate_content.
    """
    if pil_image.mode == "RGB":
        return pil_image
    if pil_image.mode in ("RGBA", "LA", "P"):
        return pil_image.convert("RGB")
    return pil_image.convert("RGB")


async def _generate_with_retry(client, model: str, contents, config, max_retries: int = GEMINI_MAX_RETRIES):
    """Call Gemini generate_content with retry logic for transient 500 errors."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            return response
        except ServerError as e:
            last_error = e
            if attempt < max_retries:
                delay = GEMINI_RETRY_BASE_DELAY ** attempt  # 2s, 4s, 8s
                print(f"Gemini 500 error on attempt {attempt}/{max_retries}. Retrying in {delay}s... Error: {e}")
                await asyncio.sleep(delay)
            else:
                print(f"Gemini 500 error on final attempt {attempt}/{max_retries}. Giving up. Error: {e}")
    raise last_error

# Configure Gemini Client
client = None
if GOOGLE_API_KEY:
    client = genai.Client(api_key=GOOGLE_API_KEY)

router = APIRouter(prefix="/ai", tags=["AI"])

# ─── Credit cost per action ──────────────────────────────────────
CREDIT_COSTS = {
    "generate_image": 5,
    "analyze_image": 2,
    "analyze_dataset_per_image": 1,
}

def _deduct_credits(supabase: Client, user_id: str, action_type: str, credits: int, prompt: str = None, metadata: dict = None):
    """Deduct credits from user balance and log the transaction + usage."""
    try:
        # 1. Get current balance
        bal_res = supabase.table("credit_balances").select("*").eq("user_id", user_id).execute()
        if not bal_res.data:
            return  # no balance row = skip (shouldn't happen for registered users)
        
        balance = bal_res.data[0]
        remaining = balance["remaining_credits"]
        
        if remaining < credits:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {credits}, have {remaining}. Upgrade your plan for more credits."
            )
        
        # 2. Update balance
        supabase.table("credit_balances").update({
            "used_credits": balance["used_credits"] + credits,
            "remaining_credits": remaining - credits,
            "updated_at": "now()"
        }).eq("user_id", user_id).execute()
        
        # 3. Log credit transaction
        supabase.table("credit_transactions").insert({
            "user_id": user_id,
            "amount": -credits,
            "type": "generation" if "generat" in action_type else "analysis",
            "description": f"{action_type}: -{credits} credits",
            "metadata": metadata or {}
        }).execute()
        
        # 4. Log usage
        supabase.table("usage_logs").insert({
            "user_id": user_id,
            "action_type": action_type,
            "prompt": prompt,
            "credits_used": credits,
            "metadata": metadata or {}
        }).execute()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Warning: Credit deduction failed: {e}")
        # Don't block the action if credit logging fails

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

        # 2. Resolve the effective dataset_id from folder_id or dataset_id
        # folder_id maps to datasets.id - when provided, it takes priority
        effective_dataset_id = request.folder_id or request.dataset_id
        
        # 2a. Fetch Dataset/Folder context if provided (including actual images as visual reference)
        dataset_context = ""
        dataset_master_prompt = ""
        reference_images = []
        unique_visual_elements = []
        folder_name = ""
        dataset_env_name = ""  # e.g. "Product", "Environment", "Character"
        dataset_image_style = ""
        dataset_theme = ""
        
        if effective_dataset_id:
            try:
                # Fetch dataset and its analyzed images for style reference
                dataset_res = supabase.table("datasets").select("*").eq("id", effective_dataset_id).single().execute()
                if dataset_res.data:
                    folder_name = dataset_res.data.get('name', '')
                    # Fetch environment name for @type/name reference context (e.g. @Product/dog)
                    env_id = dataset_res.data.get('environment_id')
                    if env_id:
                        try:
                            env_res = supabase.table("environments").select("name").eq("id", env_id).single().execute()
                            if env_res.data:
                                dataset_env_name = env_res.data.get('name', '') or ''
                        except Exception:
                            pass
                    dataset_master_prompt = dataset_res.data.get('master_prompt', '')
                    if dataset_master_prompt:
                        dataset_context = f"Style Guidelines: {dataset_master_prompt}. "
                    
                    # ── STEP A: Fetch ALL images with analysis (lightweight — no downloads yet)
                    all_images_res = supabase.table("dataset_images").select("image_url, analysis_result").eq("dataset_id", effective_dataset_id).execute()
                    
                    if all_images_res.data:
                        all_dataset_images = all_images_res.data
                        print(f"Dataset has {len(all_dataset_images)} total images")
                        
                        # ── STEP B: Semantic relevance search via Gemini Embedding API
                        # Embeds the user's prompt + every image's analysis text in one
                        # batch API call, then ranks images by cosine similarity.
                        # This finds images that are conceptually related to the prompt,
                        # even when exact keywords don't match (e.g. "model holding
                        # perfume" matches images tagged "fashion", "product", "luxury").
                        selected_images = _find_relevant_images_semantic(
                            gemini_client=client,
                            prompt=request.prompt,
                            images_data=all_dataset_images,
                            max_images=MAX_REFERENCE_IMAGES,
                        )
                        
                        # ── STEP C: Extract metadata from ALL images (for brand context),
                        #            but only DOWNLOAD the selected relevant ones
                        all_tags = []
                        vibes = []
                        lighting_styles = []
                        colors = []
                        all_descriptions = []
                        image_styles = []
                        themes = []
                        key_elements = []
                        
                        # Gather brand-level context from ALL analyzed images in the dataset
                        for img in all_dataset_images:
                            if img.get('analysis_result'):
                                analysis = img['analysis_result']
                                if 'tags' in analysis and isinstance(analysis['tags'], list):
                                    all_tags.extend(analysis['tags'])
                                if 'description' in analysis:
                                    all_descriptions.append(analysis['description'])
                                if 'vibe' in analysis:
                                    vibes.append(analysis['vibe'])
                                if 'lighting' in analysis:
                                    lighting_styles.append(analysis['lighting'])
                                if 'colors' in analysis:
                                    colors.append(analysis['colors'])
                                if 'image_style' in analysis:
                                    image_styles.append(analysis['image_style'])
                                if 'theme' in analysis:
                                    themes.append(analysis['theme'])
                                if 'key_elements' in analysis and isinstance(analysis['key_elements'], list):
                                    key_elements.extend(analysis['key_elements'])
                        
                        # ── STEP D: Download ONLY the top relevant images (saves bandwidth + time)
                        for img in selected_images:
                            if img.get('image_url'):
                                try:
                                    img_response = requests.get(img['image_url'], timeout=10)
                                    if img_response.status_code == 200:
                                        pil_image = PILImage.open(io.BytesIO(img_response.content))
                                        pil_image = _resize_image_if_needed(pil_image)
                                        reference_images.append(pil_image)
                                        print(f"Downloaded reference image ({pil_image.size[0]}x{pil_image.size[1]}): {img['image_url']}")
                                except Exception as img_error:
                                    print(f"Warning: Could not load reference image {img.get('image_url')}: {img_error}")
                        
                        # Build unique visual elements list (remove duplicates, keep most common)
                        if all_tags:
                            from collections import Counter
                            tag_counts = Counter(all_tags)
                            unique_visual_elements = [tag for tag, count in tag_counts.most_common(10)]
                            print(f"Extracted unique visual elements: {unique_visual_elements}")
                        
                        # Build unique key_elements list (remove duplicates)
                        if key_elements:
                            from collections import Counter as KeyCounter
                            ke_counts = KeyCounter(key_elements)
                            unique_key_elements = [el for el, _ in ke_counts.most_common(8)]
                        else:
                            unique_key_elements = []
                        
                        # Determine dominant image_style from dataset
                        dataset_image_style = ""
                        if image_styles:
                            from collections import Counter as StyleCounter
                            style_counts = StyleCounter(image_styles)
                            dataset_image_style = style_counts.most_common(1)[0][0]
                        
                        # Determine dominant theme from dataset
                        dataset_theme = ""
                        if themes:
                            from collections import Counter as ThemeCounter
                            theme_counts = ThemeCounter(themes)
                            dataset_theme = theme_counts.most_common(1)[0][0]
                        
                        # Build dataset_context as a CONCISE tag-based summary
                        # The actual reference images are passed as binary — no need to repeat
                        # verbose descriptions in the text prompt. Tags + keywords are enough.
                        
                        dataset_context = f"Brand: {folder_name}\n" if folder_name else ""
                        
                        if dataset_theme:
                            dataset_context += f"Theme: {dataset_theme}\n"
                        if dataset_image_style:
                            dataset_context += f"Original Visual Style: {dataset_image_style}\n"
                        
                        # Tags and key elements are the critical shorthand for the visual DNA
                        if unique_visual_elements:
                            dataset_context += f"Signature Elements: {', '.join(unique_visual_elements)}\n"
                        if unique_key_elements:
                            dataset_context += f"Key Design Features: {', '.join(unique_key_elements)}\n"
                        if colors:
                            unique_colors = list(set(colors))
                            dataset_context += f"Color Palette: {', '.join(unique_colors)}\n"
                        if vibes:
                            unique_vibes = list(set(vibes))
                            dataset_context += f"Mood: {', '.join(unique_vibes)}\n"
                        if lighting_styles:
                            unique_lighting = list(set(lighting_styles))
                            dataset_context += f"Lighting: {', '.join(unique_lighting)}\n"
                            
            except Exception as e:
                print(f"Warning: Could not fetch dataset context: {e}")
                # Continue anyway - dataset context is optional
        
        # 2b. If environment_id is provided WITHOUT a specific folder, gather broad brand context
        #     from ALL trained folders in that environment
        environment_context = ""
        if request.environment_id and not effective_dataset_id:
            try:
                env_folders_res = supabase.table("datasets").select("name, master_prompt, training_status").eq("environment_id", request.environment_id).eq("training_status", "trained").execute()
                if env_folders_res.data:
                    # Look up environment name
                    env_res = supabase.table("environments").select("name").eq("id", request.environment_id).single().execute()
                    env_name = env_res.data.get('name', 'Environment') if env_res.data else 'Environment'
                    
                    environment_context = f"--- Brand Context: {env_name} ---\n"
                    for folder in env_folders_res.data:
                        if folder.get('master_prompt'):
                            environment_context += f"[{folder['name']}]: {folder['master_prompt']}\n"
                    
                    print(f"Added environment-wide brand context from {len(env_folders_res.data)} trained folders")
            except Exception as e:
                print(f"Warning: Could not fetch environment context: {e}")
                # Continue anyway - environment context is optional

        # 3. Build the full prompt with system instruction format
        
        # Map image_style values to rich descriptive generation instructions
        IMAGE_STYLE_DESCRIPTIONS = {
            "photorealistic": "photorealistic, true-to-life, high-resolution photograph with natural detail",
            "cinematic": "cinematic film-quality image with dramatic lighting, shallow depth of field, anamorphic lens flare, and movie-like color grading",
            "illustration": "hand-drawn illustration style with clean lines and artistic detail",
            "graphic_design": "clean graphic design with bold shapes, typography-friendly composition, and flat or semi-flat aesthetics",
            "3d_render": "high-quality 3D rendered image with realistic materials, lighting, and depth",
            "watercolor": "soft watercolor painting style with fluid brush strokes and translucent color washes",
            "oil_painting": "rich oil painting style with visible brush texture, deep colors, and classical composition",
            "sketch": "detailed pencil or pen sketch with hand-drawn linework and shading",
            "pixel_art": "retro pixel art style with clean pixels and limited color palette",
            "anime": "Japanese anime/manga art style with characteristic stylized features and vivid colors",
            "vintage_film": "vintage analog film photograph with grain, muted colors, and nostalgic warmth",
            "documentary": "documentary-style candid photograph with authentic natural lighting and real-world feel",
            "editorial": "high-end editorial photography with polished styling, dramatic poses, and magazine-quality finish",
            "studio_product": "professional studio product photography with clean background, controlled lighting, and sharp detail",
            "aerial": "aerial or drone-perspective photography with sweeping top-down or elevated viewpoint",
            "macro": "extreme close-up macro photography revealing fine textures and microscopic details",
            "minimalist": "minimalist composition with clean negative space, simple forms, and restrained color palette",
            "surreal": "surrealist art style with dreamlike impossible scenes and imaginative distortions",
            "pop_art": "bold pop art style with bright colors, graphic patterns, and high contrast",
        }
        KNOWN_STYLES = set(IMAGE_STYLE_DESCRIPTIONS.keys())
        
        # Determine the image_style to use:
        #   Priority: 1) request.image_style (explicit), 2) detect from request.style (fallback),
        #             3) dataset dominant style, 4) default "photorealistic"
        effective_image_style = request.image_style
        additional_style_notes = request.style  # free-form style text for extra notes
        
        # Fallback: if image_style not set, check if request.style contains a known style name
        # This handles frontends that send "cinematic" via the style field instead of image_style
        if not effective_image_style and request.style:
            style_lower = request.style.strip().lower().replace(" ", "_").replace("-", "_")
            if style_lower in KNOWN_STYLES:
                effective_image_style = style_lower
                additional_style_notes = None  # consumed into image_style, don't duplicate
        
        # Fallback: use dataset's dominant analyzed style
        if not effective_image_style and dataset_image_style:
            effective_image_style = dataset_image_style
        
        # Final fallback
        if not effective_image_style:
            effective_image_style = "photorealistic"
        
        style_description = IMAGE_STYLE_DESCRIPTIONS.get(effective_image_style, f"{effective_image_style} style")
        print(f"Resolved image_style: {effective_image_style} (from request.image_style={request.image_style}, request.style={request.style}, dataset={dataset_image_style})")
        
        # Create a structured prompt with clear separation (matches frontend structure)
        if reference_images or unique_visual_elements:
            # === PROMPT WITH REFERENCE IMAGES ===
            # Uses Professional Commercial Photographer role with VISUAL FIDELITY RULES
            # for Character/Product/Brand-Environment consistency.
            
            system_instruction = f"""ROLE: Professional Commercial Photographer.
CORE INSTRUCTION: Generate a high-fidelity image based on the prompt: "{request.prompt}"."""
            
            if additional_style_notes:
                system_instruction += f"\nCreative direction: {additional_style_notes}"
            
            system_instruction += f"""

VISUAL FIDELITY RULES:
1. CHARACTER CONSISTENCY: If a "Character" reference is provided (e.g. @Character/person), the person in the output MUST be the same person shown in the references. Match facial features, hair, and build exactly.
2. PRODUCT CONSISTENCY: If a "Product" reference is provided (e.g. @Product/dog), the product shown MUST be the exact item from the references. Match shape, branding, and materials.
3. BRAND - ENVIRONMENT CONSISTENCY: If a "Brand - Environment" or "Environment" reference is provided (e.g. @Environment/coffee shop), the scene background and lighting MUST match the references exactly.

REFERENCE NAMING (@type/name):
The prompt may use @mentions to specify what to show. Interpret them as:
- @Product/name = the product/item from the "name" folder — show it exactly as in the reference.
- @Environment/name or @Brand-Environment/name = the scene/background from "name" — match the setting, lighting, and atmosphere.
- @Character/name = the person from "name" — match the same face, hair, and build.
Example: "make @Product/dog be inside @Environment/coffee shop with @Character/fat person" = place the dog product in a coffee shop scene, featuring the person from the character reference."""
            
            # Add current reference context when we have folder + environment names
            if folder_name and dataset_env_name:
                system_instruction += f"""

CURRENT REFERENCE: The attached images are from @{dataset_env_name}/{folder_name}. Apply the appropriate rule above — the "{folder_name}" from this {dataset_env_name} reference MUST appear/match in the generated image."""
            
            system_instruction += f"""

REFERENCE IMAGES ({len(reference_images)} attached below):
These images define the VISUAL DNA of the brand. Study them carefully and extract:
- Textures & materials (e.g. marble, wood, rattan, fabric)
- Color palette and tones
- Recurring objects, furniture, fixtures
- Spatial layout and composition patterns
- Distinctive design details
You MUST incorporate these visual elements into the generated scene."""
            
            if dataset_context.strip():
                system_instruction += f"""

REFERENCE METADATA:
{dataset_context.strip()}"""
            
            system_instruction += f"""

IMAGE STYLE: {effective_image_style} — {style_description}. The output MUST be rendered in this style.
QUALITY: Ultra high-definition commercial photography, 8k resolution, cinematic lighting."""
            
            full_prompt = system_instruction.strip()
        else:
            # === PROMPT WITHOUT DATASET (simple generation) ===
            style_suffix = ""
            if additional_style_notes:
                style_suffix = f" Creative direction: {additional_style_notes}."
            
            image_style_prefix = f"Generate a {style_description} image."
            
            # Include environment_context when available (broad brand context without specific folder)
            all_context = f"{business_context}{environment_context}{dataset_context}".strip()
            if all_context:
                full_prompt = f"{image_style_prefix}\n{all_context}\n\n{request.prompt}{style_suffix}".strip()
            else:
                full_prompt = f"{image_style_prefix}\n{request.prompt}{style_suffix}".strip()
        
        print(f"Generating image with Nano Banana Pro (Gemini 3). Prompt: {full_prompt}")
        if reference_images:
            print(f"Using {len(reference_images)} reference images from dataset")
        if unique_visual_elements:
            print(f"Incorporating {len(unique_visual_elements)} unique visual elements")
        
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
        
        # Build parts and generate. If 400 INVALID_ARGUMENT (payload too large / invalid),
        # retry once with fewer reference images (3 instead of 5).
        images_to_send = reference_images
        response = None
        
        for attempt in range(2):
            # Build parts list: text instruction FIRST, then reference images, then a final nudge
            parts = [types.Part.from_text(text=full_prompt)]
            
            uploaded_files = []  # Track uploaded files to use their URIs
            
            if images_to_send:
                # Use File API for robust handling of multiple images (avoids 20MB payload limit)
                # We upload the images to Gemini first, then reference them by URI.
                try:
                    for ref_img in images_to_send:
                        # Ensure RGB mode
                        ref_img = _ensure_rgb_image(ref_img)
                        
                        # Save to temp buffer
                        img_byte_arr = io.BytesIO()
                        ref_img.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)
                        
                        # Upload to Gemini File API
                        # We use a temporary named file to upload from memory
                        # (The SDK client.files.upload expects a file path or file-like object)
                        
                        # Since SDK might strictly require a path or file-like with name, 
                        # we'll save to a temp file on disk to be safe and robust.
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                            ref_img.save(tf.name, format="PNG")
                            tf_path = tf.name
                        
                        try:
                            print(f"Uploading reference image to Gemini File API...")
                            uploaded_file = client.files.upload(path=tf_path, config=types.UploadFileConfig(mime_type="image/png"))
                            uploaded_files.append(uploaded_file)
                            
                            # Add the file reference to the prompt parts
                            parts.append(types.Part.from_uri(
                                file_uri=uploaded_file.uri,
                                mime_type=uploaded_file.mime_type
                            ))
                        finally:
                            # Clean up local temp file
                            if os.path.exists(tf_path):
                                os.unlink(tf_path)
                    
                    # Add instruction text AFTER images as recommended in docs
                    parts.append(types.Part.from_text(
                        text=f"--- REFERENCE IMAGES ABOVE ({len(images_to_send)}) ---\n"
                             f"Now generate the scene described above. Use the visual DNA from these {len(images_to_send)} reference images "
                             f"(textures, materials, colors, objects, layout) but render the output in {effective_image_style} style."
                    ))
                    
                except Exception as upload_err:
                    print(f"File API upload failed: {upload_err}. Falling back to inline bytes.")
                    # Fallback logic if File API fails (e.g. network issue)
                    # Clear parts and uploaded_files, restart with inline bytes
                    parts = [types.Part.from_text(text=full_prompt)]
                    uploaded_files = [] # Clear any partial uploads
                    
                    parts.append(types.Part.from_text(text=f"--- REFERENCE IMAGES ({len(images_to_send)}) — study these for visual DNA ---"))
                    for ref_img in images_to_send:
                        ref_img = _ensure_rgb_image(ref_img)
                        img_byte_arr = io.BytesIO()
                        ref_img.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)
                        img_bytes = img_byte_arr.read()
                        parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
                    
                    parts.append(types.Part.from_text(
                         text=f"Now generate the scene described above. Use the visual DNA from these {len(images_to_send)} reference images (textures, materials, colors, objects, layout) but render the output in {effective_image_style} style."
                    ))
            
            contents = [types.Content(role="user", parts=parts)]
            
            try:
                response = await _generate_with_retry(
                    client=client,
                    model='gemini-3-pro-image-preview',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio=aspect_ratio,
                            image_size=resolution
                        )
                    ),
                )
                break
            except APIError as e:
                err_str = str(e)
                # 400 INVALID_ARGUMENT often from payload size or image format — retry with fewer images
                if attempt == 0 and len(images_to_send) > 3 and ("400" in err_str or "INVALID_ARGUMENT" in err_str):
                    print(f"400 INVALID_ARGUMENT with {len(images_to_send)} images, retrying with top 3...")
                    images_to_send = images_to_send[:3]
                else:
                    raise
        
        if response is None:
            raise HTTPException(status_code=500, detail="Image generation failed")
        
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
        
        # 8. Save generation record to database with full metadata
        generation_id = None
        try:
            generation_record = {
                "user_id": current_user.id if current_user else None,
                "prompt": request.prompt,
                "full_prompt": full_prompt,
                "image_url": public_url,
                "dataset_id": effective_dataset_id,
                "environment_id": request.environment_id,
                "style": request.style,
                "image_style": effective_image_style,
                "aspect_ratio": request.aspect_ratio,
                "quality": request.quality,
                "format": request.format,
                "resolution": resolution,
                "reference_images_count": len(images_to_send),
                "unique_visual_elements": unique_visual_elements if unique_visual_elements else None
            }
            
            # Insert generation record into database
            result = supabase.table("generated_images").insert(generation_record).execute()
            if result.data:
                generation_id = result.data[0].get('id')
                print(f"Saved generation record with ID: {generation_id}")
        except Exception as db_error:
            print(f"Warning: Could not save generation record: {db_error}")
            # Continue anyway - the image was generated successfully
        
        # 9. Deduct credits if user is logged in
        if current_user:
            _deduct_credits(
                supabase, str(current_user.id),
                action_type="generate_image",
                credits=CREDIT_COSTS["generate_image"],
                prompt=request.prompt,
                metadata={"generation_id": generation_id, "resolution": resolution}
            )
        
        # 10. Return the image URL and metadata (this is what the frontend expects!)
        return {
            "id": generation_id,
            "image_url": public_url,
            "caption": request.prompt,
            "prompt_used": full_prompt,
            "dataset_id": effective_dataset_id,
            "environment_id": request.environment_id,
            "folder_id": request.folder_id,
            "style": request.style,
            "image_style": effective_image_style,
            "aspect_ratio": request.aspect_ratio,
            "quality": request.quality,
            "format": request.format,
            "resolution": resolution,
            "reference_images_count": len(images_to_send),
            "credits_used": CREDIT_COSTS["generate_image"] if current_user else 0
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ServerError as e:
        print(f"Image generation failed after retries (Gemini server error): {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=503,
            detail="Image generation temporarily unavailable. Google's AI service returned a server error after multiple retries. Please try again in a few moments."
        )
    except APIError as e:
        err_str = str(e)
        print(f"Image generation failed (Gemini API error): {e}")
        import traceback
        traceback.print_exc()
        # 400 INVALID_ARGUMENT: often payload size, image format, or content policy
        if "400" in err_str or "INVALID_ARGUMENT" in err_str:
            detail = (
                "Image generation failed: the AI service rejected the request (invalid argument). "
                "Try a simpler or shorter prompt, or use a dataset with fewer reference images."
            )
        else:
            detail = f"Image generation failed due to an AI service error: {err_str}"
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:
        print(f"Image generation error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

@router.get("/generated-images")
async def get_generated_images(
    limit: int = 50,
    offset: int = 0,
    dataset_id: str = None,
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase_admin)
):
    """
    Retrieve generated images history with all metadata.
    Supports filtering by dataset_id and pagination.
    Returns: list of generated images with prompts, URLs, and generation details.
    """
    try:
        query = supabase.table("generated_images").select("*")
        
        # Filter by user if authenticated
        if current_user:
            query = query.eq("user_id", current_user.id)
        
        # Filter by dataset if provided
        if dataset_id:
            query = query.eq("dataset_id", dataset_id)
        
        # Apply pagination and ordering
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        
        result = query.execute()
        
        return {
            "images": result.data,
            "count": len(result.data),
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        print(f"Error fetching generated images: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch generated image: {str(e)}")

@router.get("/generated-images/{image_id}")
async def get_generated_image_by_id(
    image_id: str,
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase_admin)
):
    """
    Retrieve a specific generated image by ID with all metadata.
    """
    try:
        query = supabase.table("generated_images").select("*").eq("id", image_id)
        
        # Filter by user if authenticated
        if current_user:
            query = query.eq("user_id", current_user.id)
        
        result = query.single().execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Generated image not found")
        
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching generated image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch generated image: {str(e)}")

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
                    
                    prompt = """You are a universal image analysis engine. Analyze this image regardless of its subject matter — it could be architecture, food, fashion, nature, products, people, art, vehicles, technology, or anything else.

Extract the following and return as JSON:

- "description": A rich, detailed description of what the image contains — the subject, composition, setting, notable objects, textures, materials, and any distinctive visual characteristics. Be specific and thorough.
- "tags": A list of 8-12 specific, descriptive keywords covering: the primary subject, secondary elements, materials/textures, style characteristics, and any unique or distinguishing features. Use concrete nouns and adjectives (e.g., 'Exposed Brick Wall', 'Shallow Depth of Field', 'Velvet Fabric', 'Golden Hour Light', 'Minimalist Layout').
- "lighting": Specific lighting description — type (natural, artificial, studio, ambient, neon, mixed), direction (front-lit, back-lit, side-lit, overhead), quality (soft, harsh, diffused, dramatic), and color temperature (warm, cool, neutral).
- "colors": The dominant color palette as a list of 3-6 specific colors or tones (e.g., 'warm amber', 'matte black', 'dusty rose', 'forest green').
- "vibe": The overall mood, atmosphere, or emotional tone (e.g., 'cozy and intimate', 'clean and professional', 'gritty urban', 'dreamy and ethereal').
- "theme": The broad category or subject theme of the image (e.g., 'interior design', 'food photography', 'street fashion', 'landscape', 'product shot', 'portrait', 'architecture', 'abstract art').
- "image_style": Classify the visual/production style of the image into ONE of these categories: 'photorealistic', 'cinematic', 'illustration', 'graphic_design', '3d_render', 'watercolor', 'oil_painting', 'sketch', 'pixel_art', 'anime', 'vintage_film', 'documentary', 'editorial', 'studio_product', 'aerial', 'macro', 'minimalist', 'surreal', 'pop_art', or 'other'. Pick the single best match.
- "key_elements": A list of 3-5 of the most visually significant and unique elements that define this specific image — the things that make it distinctive and would need to be replicated to recreate a similar image.

Output valid JSON only. No markdown formatting."""
                    
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

    # Deduct credits for analyzed images (1 credit per image)
    if current_user and results:
        total_credits = len(results) * CREDIT_COSTS["analyze_dataset_per_image"]
        _deduct_credits(
            supabase, str(current_user.id),
            action_type="analyze_dataset",
            credits=total_credits,
            prompt=f"Analyzed {len(results)} images in dataset {actual_dataset_id}",
            metadata={"dataset_id": actual_dataset_id, "images_analyzed": len(results)}
        )

    return {"results": results, "credits_used": len(results) * CREDIT_COSTS["analyze_dataset_per_image"] if current_user else 0}

@router.post("/dataset/analyze-fast")
async def analyze_dataset_images_fast(
    request: AnalyzeDatasetRequest,
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase_admin)
):
    """
    Ultra-fast parallel analysis using Gemini 3.0 Flash.
    Optimized for maximum throughput with concurrent processing.
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

    # Reuse HTTP client for better performance
    http_client = httpx.AsyncClient(timeout=30.0, limits=httpx.Limits(max_connections=50))
    
    # Universal analysis prompt — works on any image type (not domain-specific)
    prompt = """You are a universal image analysis engine. Analyze this image regardless of subject matter — architecture, food, fashion, nature, products, people, art, vehicles, technology, or anything else.

Return JSON with:
- "tags": 8-12 specific, descriptive keywords covering the subject, materials/textures, style, and unique features. Use concrete terms (e.g., 'Exposed Brick', 'Shallow Depth of Field', 'Velvet Fabric', 'Golden Hour Light').
- "description": Detailed description of content, composition, setting, notable objects, textures, and distinctive visual characteristics.
- "lighting": Specific lighting — type (natural/artificial/studio/neon/mixed), direction, quality (soft/harsh/dramatic), and color temperature (warm/cool/neutral).
- "colors": 3-6 dominant specific colors or tones (e.g., 'warm amber', 'matte black', 'dusty rose').
- "vibe": Overall mood or emotional tone (e.g., 'cozy and intimate', 'clean and professional', 'gritty urban').
- "theme": Broad subject category (e.g., 'interior design', 'food photography', 'street fashion', 'portrait', 'product shot', 'landscape').
- "image_style": ONE of: 'photorealistic', 'cinematic', 'illustration', 'graphic_design', '3d_render', 'watercolor', 'oil_painting', 'sketch', 'pixel_art', 'anime', 'vintage_film', 'documentary', 'editorial', 'studio_product', 'aerial', 'macro', 'minimalist', 'surreal', 'pop_art', or 'other'.
- "key_elements": 3-5 most visually significant and unique elements that define this image.

Output valid JSON only."""

    async def process_single_image(image_url):
        try:
            # 1. Download image
            resp = await http_client.get(image_url)
            if resp.status_code != 200:
                return {"error": f"Download failed: {resp.status_code}", "image_url": image_url}
            
            file_content = resp.content
            content_type = resp.headers.get("content-type", "image/jpeg")

            # 2. Analyze with Gemini 3.0 Flash (minimal thinking for speed)
            if not GOOGLE_API_KEY or not client:
                return {"error": "AI not configured", "image_url": image_url}
            
            try:
                parts = [
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=file_content, mime_type=content_type)
                ]
                
                # Use minimal thinking level for maximum speed
                response = client.models.generate_content(
                    model='gemini-3-flash-preview',
                    contents=[types.Content(role="user", parts=parts)],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        thinking_config=types.ThinkingConfig(thinking_level="minimal")
                    )
                )
                
                analysis_result = json.loads(response.text)
                    
            except Exception as ai_error:
                print(f"AI Analysis failed for {image_url}: {ai_error}")
                return {"error": str(ai_error), "image_url": image_url}
            
            # 3. Store in DB
            data = {
                "dataset_id": request.dataset_id,
                "image_url": image_url,
                "analysis_result": analysis_result
            }
            
            res = supabase.table("dataset_images").insert(data).execute()
            return res.data[0] if res.data else None
                
        except Exception as e:
            print(f"Error processing {image_url}: {e}")
            return {"error": str(e), "image_url": image_url}

    try:
        # Process with higher concurrency (20 at a time for maximum speed)
        semaphore = asyncio.Semaphore(20)
        
        async def sem_process(url):
            async with semaphore:
                return await process_single_image(url)

        results = await asyncio.gather(*[sem_process(url) for url in request.image_urls])
        
        # Filter out error results
        valid_results = [r for r in results if r and "error" not in r]
        
        # Deduct credits for successfully analyzed images
        if current_user and valid_results:
            total_credits = len(valid_results) * CREDIT_COSTS["analyze_dataset_per_image"]
            _deduct_credits(
                supabase, str(current_user.id),
                action_type="analyze_dataset_fast",
                credits=total_credits,
                prompt=f"Fast-analyzed {len(valid_results)} images in dataset {request.dataset_id}",
                metadata={"dataset_id": request.dataset_id, "images_analyzed": len(valid_results)}
            )
        
        return {
            "results": valid_results, 
            "total_processed": len(request.image_urls), 
            "successful": len(valid_results),
            "credits_used": len(valid_results) * CREDIT_COSTS["analyze_dataset_per_image"] if current_user else 0
        }
    
    finally:
        # Clean up HTTP client
        await http_client.aclose()

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

@router.patch("/dataset/{dataset_id}/training-status")
async def update_dataset_training_status(
    dataset_id: str,
    training_status: str = Form(...),
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase_admin)
):
    """
    Update the training status of a dataset.
    Allows users to mark a dataset as 'trained' or 'not_trained' from the frontend.
    This is a simple status flag to track whether the user has completed training on this dataset.
    """
    # Validate training_status
    if training_status not in ["trained", "not_trained"]:
        raise HTTPException(
            status_code=400, 
            detail="training_status must be either 'trained' or 'not_trained'"
        )
    
    try:
        # Check if dataset exists
        ds_check = supabase.table("datasets").select("id, user_id").eq("id", dataset_id).execute()
        
        if not ds_check.data:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        dataset = ds_check.data[0]
        
        # Optional: Verify ownership if user is logged in
        if current_user and dataset.get("user_id") and dataset["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You don't have permission to update this dataset")
        
        # Update the training status
        update_res = supabase.table("datasets").update({
            "training_status": training_status
        }).eq("id", dataset_id).execute()
        
        if not update_res.data:
            raise HTTPException(status_code=500, detail="Failed to update training status")
        
        return {
            "success": True,
            "dataset_id": dataset_id,
            "training_status": training_status,
            "message": f"Dataset training status updated to '{training_status}'"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating training status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update training status: {str(e)}")

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

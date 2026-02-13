from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List
import uuid
import json
import base64
import requests
import re
import difflib
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
MAX_REFERENCE_IMAGES = 14         # Gemini 3 Pro supports up to 14 reference images
MAX_IMAGE_DIMENSION = 1024        # Resize large images to this max width/height
GEMINI_MAX_RETRIES = 3            # Retry transient 500 errors up to 3 times
GEMINI_RETRY_BASE_DELAY = 2      # Base delay in seconds (exponential backoff)
EMBED_BATCH_SIZE = 200            # Batch embeddings for large datasets
MAX_DATASET_IMAGES_FETCH = 5000   # Safety cap when scanning large datasets
HYBRID_CANDIDATE_MULTIPLIER = 3   # Semantic prefilter pool size before vision rerank
VISION_RERANK_BATCH_SIZE = 8      # Images per Gemini vision rerank call
VISION_RERANK_MAX_RETRIES = 3     # Retry vision rerank batch calls
VISION_RERANK_RETRY_BASE_DELAY = 2  # Base delay for vision rerank retry backoff
MENTION_FUZZY_CUTOFF = 0.72       # Fuzzy threshold for mention-to-dataset matching


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


def _normalize_lookup_text(value: str) -> str:
    """Normalize text for robust exact/fuzzy matching."""
    if not value:
        return ""
    return " ".join(value.lower().strip().split())


def _trim_mention_phrase(raw: str) -> str:
    """
    Trim noisy trailing words from @mentions captured in free-form prompts.
    Example: "sauban standing in front of" -> "sauban"
    """
    if not raw:
        return ""
    text = raw.strip().strip("/").strip()
    text = re.sub(r"\s+", " ", text)

    stop_words = {
        "standing", "holding", "wearing", "with", "without", "in", "on", "at",
        "front", "of", "near", "beside", "behind", "under", "over", "and",
        "context", "business", "theme", "vibe", "customer", "prompt",
    }
    tokens = text.split(" ")
    kept = []
    for token in tokens:
        t = token.lower().strip()
        if t.endswith(":"):
            break
        if t in stop_words:
            break
        kept.append(token)
        if len(kept) >= 6:
            break
    return " ".join(kept).strip()


def _extract_prompt_dataset_mentions(prompt: str) -> tuple[list[tuple[str, str]], list[str]]:
    """
    Extract potential dataset mentions from prompt text.
    Supports:
      - Path style: @Environment/Folder
      - Folder style: @FolderName
    """
    if not prompt:
        return [], []

    path_mentions = []
    plain_mentions = []

    # Path mentions like @Character/sauban or @new environment/braun notes
    path_pattern = re.compile(
        r"@\s*([A-Za-z0-9][A-Za-z0-9 _-]{0,64})\s*/\s*([A-Za-z0-9][A-Za-z0-9 _-]{0,96})"
    )
    for match in path_pattern.finditer(prompt):
        env_raw = _trim_mention_phrase(match.group(1))
        folder_raw = _trim_mention_phrase(match.group(2))
        if env_raw and folder_raw:
            path_mentions.append((env_raw, folder_raw))

    # Plain mentions like @sauban (skip those that are actually @env/folder)
    plain_pattern = re.compile(r"@\s*([A-Za-z0-9][A-Za-z0-9 _-]{0,96})(?!\s*/)")
    for match in plain_pattern.finditer(prompt):
        mention = _trim_mention_phrase(match.group(1))
        if not mention:
            continue
        mention_norm = _normalize_lookup_text(mention)
        if mention_norm in {"business context", "business", "theme", "vibe", "customer", "n a", "na"}:
            continue
        plain_mentions.append(mention)

    # De-duplicate while preserving order
    seen_path = set()
    uniq_path = []
    for env_name, folder_name in path_mentions:
        key = (_normalize_lookup_text(env_name), _normalize_lookup_text(folder_name))
        if key not in seen_path:
            seen_path.add(key)
            uniq_path.append((env_name, folder_name))

    seen_plain = set()
    uniq_plain = []
    for mention in plain_mentions:
        key = _normalize_lookup_text(mention)
        if key not in seen_plain:
            seen_plain.add(key)
            uniq_plain.append(mention)

    return uniq_path, uniq_plain


def _fuzzy_match_key(query: str, keys: list[str], cutoff: float = MENTION_FUZZY_CUTOFF) -> str | None:
    """Return best fuzzy key match or None."""
    if not query or not keys:
        return None
    query_norm = _normalize_lookup_text(query)
    if query_norm in keys:
        return query_norm
    match = difflib.get_close_matches(query_norm, keys, n=1, cutoff=cutoff)
    return match[0] if match else None


def _match_dataset_by_name(query: str, datasets: list[dict]) -> dict | None:
    """Match a folder name to the best dataset row using exact/contains/fuzzy."""
    if not query or not datasets:
        return None
    query_norm = _normalize_lookup_text(query)

    by_norm = {}
    for ds in datasets:
        ds_name_norm = _normalize_lookup_text(ds.get("name", ""))
        if not ds_name_norm:
            continue
        by_norm.setdefault(ds_name_norm, []).append(ds)

    if query_norm in by_norm:
        return by_norm[query_norm][0]

    for ds_name_norm, rows in by_norm.items():
        if query_norm in ds_name_norm or ds_name_norm in query_norm:
            return rows[0]

    best_key = _fuzzy_match_key(query_norm, list(by_norm.keys()))
    if best_key:
        return by_norm[best_key][0]
    return None


def _resolve_referenced_dataset_ids(
    supabase: Client,
    prompt: str,
    current_user=None,
    explicit_dataset_ids: list[str] | None = None,
) -> list[str]:
    """
    Resolve all dataset IDs referenced in prompt @mentions.
    Combines explicit IDs (folder_id/dataset_id) + prompt references.
    """
    resolved_ids = []
    for ds_id in (explicit_dataset_ids or []):
        if ds_id and ds_id not in resolved_ids:
            resolved_ids.append(ds_id)

    if not prompt:
        return resolved_ids

    try:
        ds_query = supabase.table("datasets").select("id, name, environment_id, user_id")
        env_query = supabase.table("environments").select("id, name, user_id")
        if current_user:
            user_id = str(current_user.id)
            ds_query = ds_query.eq("user_id", user_id)
            env_query = env_query.eq("user_id", user_id)

        datasets = ds_query.execute().data or []
        environments = env_query.execute().data or []
        if not datasets:
            return resolved_ids

        env_name_to_ids = {}
        for env in environments:
            env_name_norm = _normalize_lookup_text(env.get("name", ""))
            if env_name_norm:
                env_name_to_ids.setdefault(env_name_norm, []).append(env.get("id"))

        datasets_by_env = {}
        for ds in datasets:
            datasets_by_env.setdefault(ds.get("environment_id"), []).append(ds)

        path_mentions, plain_mentions = _extract_prompt_dataset_mentions(prompt)

        matched_descriptions = []

        # Resolve @Environment/Folder references first
        for env_name, folder_name in path_mentions:
            env_key = _fuzzy_match_key(_normalize_lookup_text(env_name), list(env_name_to_ids.keys()))
            env_ids = env_name_to_ids.get(env_key, []) if env_key else []

            candidate_datasets = []
            for env_id in env_ids:
                candidate_datasets.extend(datasets_by_env.get(env_id, []))
            if not candidate_datasets:
                candidate_datasets = datasets

            matched = _match_dataset_by_name(folder_name, candidate_datasets)
            if matched and matched.get("id") not in resolved_ids:
                resolved_ids.append(matched["id"])
                matched_descriptions.append(f"@{env_name}/{folder_name} -> {matched.get('name')}")

        # Resolve @Folder references
        for mention in plain_mentions:
            matched = _match_dataset_by_name(mention, datasets)
            if matched and matched.get("id") not in resolved_ids:
                resolved_ids.append(matched["id"])
                matched_descriptions.append(f"@{mention} -> {matched.get('name')}")

        if matched_descriptions:
            print("Resolved prompt references: " + "; ".join(matched_descriptions))

        return resolved_ids

    except Exception as e:
        print(f"Warning: Could not resolve prompt references: {e}")
        return resolved_ids


def _build_relevance_query(
    prompt: str,
    image_style: str = "",
    style_notes: str = "",
    folder_name: str = "",
    dataset_master_prompt: str = "",
) -> str:
    """
    Build a focused retrieval query for semantic image ranking.
    This follows Gemini prompt fundamentals: clear intent + explicit constraints.
    """
    parts = [f"User request: {prompt.strip()}"]
    if image_style:
        parts.append(f"Preferred visual production style: {image_style}")
    if style_notes:
        parts.append(f"Additional style constraints: {style_notes}")
    if folder_name:
        parts.append(f"Dataset context: {folder_name}")
    if dataset_master_prompt:
        parts.append(f"Dataset master prompt: {dataset_master_prompt}")
    return ". ".join(parts)


def _extract_json_text(raw_text: str) -> str:
    """Extract JSON payload from plain/fenced model output."""
    if not raw_text:
        return ""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


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
      1. Build search text from image analysis_result
         (tags, description, key_elements, theme, style, vibe, colors, lighting).
      2. Embed the prompt once.
      3. Embed image texts in batches (scales to large folders).
      4. Score each image by cosine similarity, sort descending, return top N.
    
    Falls back to returning the first N images if embedding fails.
    """
    # Build search text for each image
    scorable = []      # list[(img, search_text)] for analyzed images
    fallback_only = [] # images without usable analysis_result text
    
    for img in images_data:
        analysis = img.get('analysis_result', {})
        search_text = _build_image_search_text(analysis)
        if search_text:
            scorable.append((img, search_text))
        else:
            fallback_only.append(img)
    
    if not scorable:
        print("No analyzed images found — using first images as fallback")
        return images_data[:max_images]
    
    try:
        prompt_embed = gemini_client.models.embed_content(
            model="gemini-embedding-001",
            contents=[prompt],
            config=types.EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY",
            ),
        )
        prompt_embedding = prompt_embed.embeddings[0].values
        
        print(f"Ranking {len(scorable)} analyzed images with Gemini embeddings (batch size={EMBED_BATCH_SIZE})...")

        # Score each image by cosine similarity to the prompt, in batches
        scored = []
        for start in range(0, len(scorable), EMBED_BATCH_SIZE):
            batch = scorable[start:start + EMBED_BATCH_SIZE]
            batch_texts = [search_text for _, search_text in batch]
            batch_embed = gemini_client.models.embed_content(
                model="gemini-embedding-001",
                contents=batch_texts,
                config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
            )
            for (img, _), img_embedding in zip(batch, batch_embed.embeddings):
                similarity = _cosine_similarity(prompt_embedding, img_embedding.values)
                scored.append((similarity, img))
        
        # Sort by similarity descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Select top N
        selected_scored = scored[:max_images]
        selected_images = [img for _, img in selected_scored]

        # If we still need images, append non-analyzed images as fallback
        if len(selected_images) < max_images and fallback_only:
            needed = max_images - len(selected_images)
            selected_images.extend(fallback_only[:needed])
        
        print(f"Semantic relevance ranking — selected {len(selected_images)} of {len(images_data)} images:")
        for rank, (sim, img) in enumerate(selected_scored, 1):
            url = img.get('image_url', 'N/A')
            short_url = url.split('/')[-1] if url else 'N/A'
            # Show a few top tags for context
            tags = img.get('analysis_result', {}).get('tags', [])
            top_tags = ', '.join(tags[:4]) if tags else 'no tags'
            print(f"  #{rank}: similarity={sim:.4f}  [{top_tags}]  {short_url}")
        
        return selected_images
        
    except Exception as e:
        # If embedding fails (API error, quota, etc.), fall back to first N
        print(f"Warning: Semantic search failed ({e}), falling back to first {max_images} images")
        return images_data[:max_images]


def _rerank_images_with_vision(
    gemini_client,
    prompt: str,
    images_data: list,
    max_images: int = MAX_REFERENCE_IMAGES,
) -> list:
    """
    Vision rerank stage (direct image understanding).
    Input should be semantic-prefiltered candidates.
    """
    if not images_data:
        return []
    if len(images_data) <= max_images:
        return images_data[:max_images]

    scored = []
    scored_ids = set()
    hard_failure = False

    for start in range(0, len(images_data), VISION_RERANK_BATCH_SIZE):
        batch = images_data[start:start + VISION_RERANK_BATCH_SIZE]
        parts = []

        instruction = (
            "Rank candidate reference images for generation relevance.\n"
            f"User request: {prompt}\n\n"
            "For each candidate image, assign a relevance score from 0.0 to 1.0 where:\n"
            "- 1.0 = highly aligned with subject/theme/style/composition/lighting\n"
            "- 0.0 = unrelated\n\n"
            "Return strict JSON only in this exact shape:\n"
            "{\"scores\":[{\"candidate\":1,\"score\":0.92}]}\n"
            "Use the candidate number shown before each image."
        )
        parts.append(types.Part.from_text(text=instruction))

        local_idx_to_img = {}
        local_idx = 1
        for img in batch:
            image_url = img.get("image_url")
            if not image_url:
                continue
            try:
                img_response = requests.get(image_url, timeout=10)
                if img_response.status_code != 200:
                    continue

                mime_type = img_response.headers.get("content-type", "image/jpeg").split(";")[0].strip().lower()
                if not mime_type.startswith("image/"):
                    mime_type = "image/jpeg"

                parts.append(types.Part.from_text(text=f"Candidate {local_idx}"))
                parts.append(types.Part.from_bytes(data=img_response.content, mime_type=mime_type))
                local_idx_to_img[local_idx] = img
                local_idx += 1
            except Exception as img_err:
                print(f"Warning: Vision rerank could not load image {image_url}: {img_err}")

        if not local_idx_to_img:
            continue

        response = None
        for attempt in range(1, VISION_RERANK_MAX_RETRIES + 1):
            try:
                response = gemini_client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=[types.Content(role="user", parts=parts)],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        thinking_config=types.ThinkingConfig(thinking_level="minimal")
                    )
                )
                break
            except Exception as rerank_err:
                if attempt < VISION_RERANK_MAX_RETRIES:
                    delay = VISION_RERANK_RETRY_BASE_DELAY ** attempt
                    print(
                        f"Vision rerank batch failed on attempt {attempt}/{VISION_RERANK_MAX_RETRIES}. "
                        f"Retrying in {delay}s... Error: {rerank_err}"
                    )
                    time.sleep(delay)
                else:
                    print(
                        f"Vision rerank batch failed on final attempt {attempt}/{VISION_RERANK_MAX_RETRIES}. "
                        f"Falling back to semantic order. Error: {rerank_err}"
                    )
                    hard_failure = True

        if hard_failure:
            break

        try:
            parsed_text = _extract_json_text(response.text if response and response.text else "")
            parsed = json.loads(parsed_text) if parsed_text else {}
            raw_scores = parsed.get("scores", []) if isinstance(parsed, dict) else []
            score_map = {}
            for row in raw_scores:
                if not isinstance(row, dict):
                    continue
                try:
                    c = int(row.get("candidate"))
                    s = float(row.get("score"))
                    # Clamp scores to expected range
                    score_map[c] = max(0.0, min(1.0, s))
                except Exception:
                    continue

            for c, img in local_idx_to_img.items():
                vision_score = score_map.get(c, 0.0)
                scored.append((vision_score, img))
                scored_ids.add(id(img))

        except Exception as parse_err:
            print(f"Warning: Vision rerank response parsing failed: {parse_err}")
            hard_failure = True
            break

    # If vision rerank couldn't complete reliably, use semantic order directly.
    if hard_failure or not scored:
        print("Vision rerank unavailable after retries — using semantic selection fallback")
        return images_data[:max_images]

    # Preserve semantic order as fallback for unscored images
    for img in images_data:
        if id(img) not in scored_ids:
            scored.append((0.0, img))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [img for _, img in scored[:max_images]]

    print(f"Vision rerank selected {len(selected)} references from {len(images_data)} semantic candidates")
    return selected


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
        # 1. Resolve all referenced datasets:
        #    - explicit folder_id / dataset_id
        #    - @mentions in prompt (supports multiple references)
        explicit_dataset_ids = []
        if request.folder_id:
            explicit_dataset_ids.append(request.folder_id)
        if request.dataset_id and request.dataset_id not in explicit_dataset_ids:
            explicit_dataset_ids.append(request.dataset_id)
        resolved_dataset_ids = _resolve_referenced_dataset_ids(
            supabase=supabase,
            prompt=request.prompt,
            current_user=current_user,
            explicit_dataset_ids=explicit_dataset_ids,
        )
        primary_dataset_id = resolved_dataset_ids[0] if resolved_dataset_ids else None
        
        # Resolve style early so retrieval can include it
        effective_image_style = request.image_style or "photorealistic"
        additional_style_notes = request.style

        # 2a. Fetch images from all resolved datasets and select top 14 references
        # Uses Gemini embeddings over analyzed image metadata to improve consistency.
        reference_images = []
        folder_name = ""
        dataset_master_prompt = ""
        
        if resolved_dataset_ids:
            try:
                all_images_data = []
                dataset_names = []
                master_prompts = []

                for ds_id in resolved_dataset_ids:
                    dataset_res = (
                        supabase
                        .table("datasets")
                        .select("name, master_prompt")
                        .eq("id", ds_id)
                        .single()
                        .execute()
                    )
                    if not dataset_res.data:
                        continue

                    ds_name = dataset_res.data.get("name", "") or ""
                    ds_master_prompt = dataset_res.data.get("master_prompt", "") or ""
                    if ds_name:
                        dataset_names.append(ds_name)
                    if ds_master_prompt:
                        master_prompts.append(ds_master_prompt)

                    page_size = 1000
                    start = 0
                    while start < MAX_DATASET_IMAGES_FETCH:
                        end = min(start + page_size - 1, MAX_DATASET_IMAGES_FETCH - 1)
                        page_res = (
                            supabase
                            .table("dataset_images")
                            .select("image_url, analysis_result, created_at")
                            .eq("dataset_id", ds_id)
                            .range(start, end)
                            .execute()
                        )
                        page_data = page_res.data or []
                        if not page_data:
                            break
                        for row in page_data:
                            row["source_dataset_id"] = ds_id
                            row["source_dataset_name"] = ds_name
                        all_images_data.extend(page_data)
                        if len(page_data) < page_size:
                            break
                        start += page_size

                if all_images_data:
                    folder_name = ", ".join(dataset_names[:10])
                    dataset_master_prompt = " | ".join(master_prompts[:6])
                    print(
                        f"Resolved {len(resolved_dataset_ids)} dataset references "
                        f"with {len(all_images_data)} total images (selecting top {MAX_REFERENCE_IMAGES})"
                    )

                    retrieval_query = _build_relevance_query(
                        prompt=request.prompt,
                        image_style=effective_image_style,
                        style_notes=additional_style_notes or "",
                        folder_name=folder_name,
                        dataset_master_prompt=dataset_master_prompt,
                    )

                    semantic_pool_size = min(
                        len(all_images_data),
                        max(MAX_REFERENCE_IMAGES, MAX_REFERENCE_IMAGES * HYBRID_CANDIDATE_MULTIPLIER)
                    )
                    semantic_candidates = _find_relevant_images_semantic(
                        gemini_client=client,
                        prompt=retrieval_query,
                        images_data=all_images_data,
                        max_images=semantic_pool_size,
                    )
                    ranked_images = _rerank_images_with_vision(
                        gemini_client=client,
                        prompt=retrieval_query,
                        images_data=semantic_candidates,
                        max_images=MAX_REFERENCE_IMAGES,
                    )

                    # Download the ranked references
                    for img in ranked_images:
                        if img.get('image_url'):
                            try:
                                img_response = requests.get(img['image_url'], timeout=10)
                                if img_response.status_code == 200:
                                    pil_image = PILImage.open(io.BytesIO(img_response.content))
                                    pil_image = _resize_image_if_needed(pil_image)
                                    reference_images.append(pil_image)
                                    print(
                                        f"Selected reference image from '{img.get('source_dataset_name', 'dataset')}' "
                                        f"({pil_image.size[0]}x{pil_image.size[1]}): {img['image_url']}"
                                    )
                            except Exception as img_error:
                                print(f"Warning: Could not load reference image {img.get('image_url')}: {img_error}")
                    
                    print(f"Loaded {len(reference_images)} reference images for generation")
                            
            except Exception as e:
                print(f"Warning: Could not fetch dataset images: {e}")
                # Continue anyway - reference images are optional
        
        # 3. Build the prompt — keep it simple, let the images do the work
        # Following Gemini docs pattern: short prompt + reference images
        # https://ai.google.dev/gemini-api/docs/image-generation
        
        if reference_images:
            # === PROMPT WITH REFERENCE IMAGES ===
            # Follow Gemini prompt best-practices:
            # - clear intent
            # - explicit constraints
            # - output target grounded by references
            full_prompt = (
                "Using the provided reference images as visual ground truth, generate one final image. "
                "Preserve the most important subject identity, composition language, lighting behavior, "
                "texture/material treatment, and overall color palette from those references. "
                f"User request: {request.prompt}. "
                f"Target style class: {effective_image_style}."
            )
            if additional_style_notes:
                full_prompt += f" Additional style notes: {additional_style_notes}."
            
            print(f"Using reference-image prompt with {len(reference_images)} images")
        else:
            # === PROMPT WITHOUT REFERENCE IMAGES (text-to-image) ===
            style_suffix = ""
            if additional_style_notes:
                style_suffix = f" {additional_style_notes} style."
            
            full_prompt = f"{request.prompt}{style_suffix}".strip()
        
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
        
        # Build parts: [prompt, image1, image2, ...] — following Gemini docs pattern
        # https://ai.google.dev/gemini-api/docs/image-generation#use-up-to-14-reference-images
        images_to_send = reference_images
        response = None
        
        for attempt in range(2):
            # Prompt text first, then reference images (no trailing text)
            parts = [types.Part.from_text(text=full_prompt)]
            
            uploaded_files = []  # Track uploaded files for cleanup
            
            if images_to_send:
                # Use File API to handle multiple images (avoids 20MB payload limit)
                try:
                    for ref_img in images_to_send:
                        ref_img = _ensure_rgb_image(ref_img)
                        
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                            ref_img.save(tf.name, format="PNG")
                            tf_path = tf.name
                        
                        try:
                            print(f"Uploading reference image to Gemini File API...")
                            uploaded_file = client.files.upload(path=tf_path, config=types.UploadFileConfig(mime_type="image/png"))
                            uploaded_files.append(uploaded_file)
                            parts.append(types.Part.from_uri(
                                file_uri=uploaded_file.uri,
                                mime_type=uploaded_file.mime_type
                            ))
                        finally:
                            if os.path.exists(tf_path):
                                os.unlink(tf_path)
                    
                except Exception as upload_err:
                    print(f"File API upload failed: {upload_err}. Falling back to inline bytes.")
                    parts = [types.Part.from_text(text=full_prompt)]
                    uploaded_files = []
                    
                    for ref_img in images_to_send:
                        ref_img = _ensure_rgb_image(ref_img)
                        img_byte_arr = io.BytesIO()
                        ref_img.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)
                        parts.append(types.Part.from_bytes(data=img_byte_arr.read(), mime_type="image/png"))
            
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
                "dataset_id": primary_dataset_id,
                "environment_id": request.environment_id,
                "style": request.style,
                "image_style": effective_image_style,
                "aspect_ratio": request.aspect_ratio,
                "quality": request.quality,
                "format": request.format,
                "resolution": resolution,
                "reference_images_count": len(images_to_send),
                "unique_visual_elements": None
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
            "dataset_id": primary_dataset_id,
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

# ✨ Upgraded to Gemini 3 Pro Image Preview (Nano Banana Pro)

## What Changed

**From:** `gemini-2.5-flash-image` (Nano Banana)  
**To:** `gemini-3-pro-image-preview` (Nano Banana Pro)

---

## Why This is Better

### 🎨 Professional Asset Production
- **Advanced Reasoning:** "Thinking" mode for complex prompts
- **High-Resolution:** 1K, 2K, and 4K output
- **Better Text Rendering:** Legible, stylized text in images
- **Superior Quality:** State-of-the-art image generation

### 🖼️ More Reference Images
- **Up to 14 reference images** (vs 5 before)
  - Up to 6 images of objects with high-fidelity
  - Up to 5 images of humans for character consistency

### 🔍 Advanced Features
- **Grounding with Google Search:** Real-time data integration
- **Thinking Process:** Generates interim images to refine composition
- **Complex Instructions:** Better at following detailed prompts
- **Multi-turn Editing:** Conversational image refinement

---

## Code Changes

### Model Selection
```python
# Before (Flash)
model = genai.GenerativeModel('gemini-2.5-flash-image')

# After (Pro)
model = genai.GenerativeModel('gemini-3-pro-image-preview')
```

### Generation Config
```python
# Now includes proper config for Gemini 3 Pro
generation_config = {
    "response_modalities": ["TEXT", "IMAGE"],
    "image_config": {
        "aspect_ratio": "1:1",  # or any supported ratio
        "image_size": "2K"      # 1K, 2K, or 4K
    }
}

response = model.generate_content(
    content_parts,
    generation_config=generation_config
)
```

### Content Order
```python
# Gemini 3 Pro prefers text first, then images
content_parts = [
    full_prompt,        # Text prompt first
    image1,             # Reference images after
    image2,
    image3,
    ...
]
```

---

## API Request Format

### Using Your API Key

**API Key:** `AIzaSyA4H5MCRTb0FGaydsRTI04STmbRhyRUr_o`

### REST API Format (Direct)

```bash
curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent" \
  -H "x-goog-api-key: AIzaSyA4H5MCRTb0FGaydsRTI04STmbRhyRUr_o" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [
        {"text": "a latte with latte art on a marble table"},
        {"inline_data": {"mime_type": "image/jpeg", "data": "<BASE64_IMAGE_1>"}},
        {"inline_data": {"mime_type": "image/jpeg", "data": "<BASE64_IMAGE_2>"}}
      ]
    }],
    "generationConfig": {
      "responseModalities": ["TEXT", "IMAGE"],
      "imageConfig": {
        "aspectRatio": "1:1",
        "imageSize": "2K"
      }
    }
  }'
```

### Your Backend API (Easier)

```bash
curl -X POST http://localhost:8000/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a latte with latte art",
    "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
    "aspect_ratio": "1:1"
  }'
```

Your backend automatically:
- Fetches reference images from dataset
- Converts them to proper format
- Adds business profile context
- Calls Gemini 3 Pro with correct config
- Returns the generated image URL

---

## Resolution Options

| Resolution | Size | Use Case |
|------------|------|----------|
| 1K | 1024x1024 (1:1) | Quick previews, social media |
| 2K | 2048x2048 (1:1) | High-quality posts, marketing |
| 4K | 4096x4096 (1:1) | Professional prints, large displays |

**Default:** 2K (good balance of quality and speed)

---

## Aspect Ratios Supported

All the same aspect ratios as before:
- 1:1, 16:9, 9:16, 4:3, 3:4
- 2:3, 3:2, 4:5, 5:4, 21:9

**Resolution varies by aspect ratio** (see Gemini docs for exact dimensions)

---

## Performance

| Model | Speed | Quality | Resolution | Cost |
|-------|-------|---------|------------|------|
| Flash (old) | ⚡ Fast | ⭐⭐⭐ Good | 1024px | $ Lower |
| **Pro (new)** | 🐢 Slower | ⭐⭐⭐⭐⭐ Excellent | Up to 4K | $$ Higher |

**Trade-off:** Slightly slower but MUCH better quality

---

## Test the Upgrade

```bash
# Test with your dataset
curl -X POST http://localhost:8000/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a latte with heart-shaped latte art on a black marble table",
    "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
    "aspect_ratio": "1:1"
  }'
```

**Expected Server Logs:**
```
Generating image with Nano Banana Pro (Gemini 3). Prompt: ...
Using 5 reference images from dataset
Added reference image: https://...
```

**Expected Response:**
```json
{
  "image_url": "https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/generated-images/generated/xyz-789.png",
  "prompt_used": "Style Guidelines: ... Match the style and aesthetic of the 5 reference image(s) provided. a latte with heart-shaped latte art on a black marble table",
  "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a"
}
```

---

## What to Expect

### Better Quality
- ✅ More realistic textures
- ✅ Better lighting and shadows
- ✅ More accurate style matching
- ✅ Higher resolution (2K default)

### Advanced Features
- ✅ Better text rendering (if you add text to images)
- ✅ More complex compositions
- ✅ Better understanding of prompts
- ✅ Thinking process for refinement

### Reference Images
- ✅ Can use up to 14 images (currently using 5)
- ✅ Better style consistency
- ✅ More accurate color matching
- ✅ Better composition understanding

---

## Pricing

**Gemini 3 Pro Image Preview:**
- **Input:** ~1120 tokens per image (varies by resolution)
- **Output:** Image generation cost
- **Pricing:** See [Google AI Pricing](https://ai.google.dev/pricing)

**Note:** Pro model is more expensive but produces professional-quality results

---

## Future Enhancements

### Can Add Later:
1. **Resolution Selection:**
   ```json
   {
     "prompt": "...",
     "resolution": "4K"  // User can choose 1K, 2K, or 4K
   }
   ```

2. **More Reference Images:**
   ```python
   # Currently using 5, can use up to 14
   images_res = supabase.table("dataset_images")
     .select("image_url, analysis_result")
     .eq("dataset_id", request.dataset_id)
     .limit(14)  # Increase from 5 to 14
     .execute()
   ```

3. **Google Search Grounding:**
   ```python
   # Add Google Search for real-time data
   tools = [{"google_search": {}}]
   ```

---

## Troubleshooting

### Error: "Model not found"
**Solution:** Make sure you're using the correct API key and model name

### Error: "Invalid generation_config"
**Solution:** Already fixed! The config format is now correct for Gemini 3 Pro

### Slow Generation
**Expected:** Gemini 3 Pro is slower but produces better results
- With reference images: ~10-15 seconds
- Without reference images: ~5-10 seconds

---

## Summary

### ✅ What's Better
- Professional-quality images (2K resolution)
- Advanced reasoning and thinking mode
- Better style matching with reference images
- Support for up to 14 reference images
- Better text rendering
- More accurate prompt following

### ⚠️ Trade-offs
- Slightly slower generation
- Higher cost per image
- But MUCH better quality!

---

## Files Modified

**File:** `app/routers/ai.py`

**Changes:**
1. Model: `gemini-2.5-flash-image` → `gemini-3-pro-image-preview`
2. Added proper `generation_config` with `response_modalities` and `image_config`
3. Changed content order (text first, then images)
4. Added resolution support (2K default)
5. Updated logging messages

---

## Ready to Test!

```bash
# 1. Server should auto-reload (if using --reload)
# If not, restart:
uvicorn app.main:app --reload

# 2. Test with dataset
curl -X POST http://localhost:8000/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a latte with latte art",
    "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
    "aspect_ratio": "1:1"
  }'
```

**You're now using the professional-grade Gemini 3 Pro Image model!** 🎨✨

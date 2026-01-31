# Image Generation Setup Guide

## Overview

The `/ai/generate` endpoint now uses **Imagen 3** (Google's state-of-the-art image generation model) via the Gemini API to generate high-quality images.

## What Was Fixed

### Before (Broken):
```python
return {"message": "Image generation initiated", "prompt_used": full_prompt}
```
- ❌ No actual image generation
- ❌ No image URL returned
- ❌ Frontend couldn't display anything

### After (Working):
```python
return {
    "image_url": public_url,  # Actual image URL!
    "caption": request.prompt,
    "prompt_used": full_prompt,
    "dataset_id": request.dataset_id,
    "style": request.style,
    "aspect_ratio": request.aspect_ratio
}
```
- ✅ Generates image with Imagen 3
- ✅ Uploads to Supabase storage
- ✅ Returns public URL
- ✅ Frontend can display the image

---

## Setup Requirements

### 1. Install Dependencies

The following packages were added to `requirements.txt`:
- `pillow` - For image processing

Install with:
```bash
pip install -r requirements.txt
```

### 2. Create Supabase Storage Bucket

You need to create a storage bucket for generated images:

**Steps:**
1. Go to https://supabase.com/dashboard/project/qxripdllxckfpnimzxoa/storage/buckets
2. Click "New bucket"
3. Name: `generated-images`
4. Public bucket: ✅ **Yes** (so images are publicly accessible)
5. Click "Create bucket"

**Set Storage Policies:**

After creating the bucket, set these policies:

```sql
-- Allow public uploads (for service role)
CREATE POLICY "Allow service role uploads"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'generated-images');

-- Allow public reads
CREATE POLICY "Allow public reads"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'generated-images');
```

### 3. Run Database Migration (If Not Done)

Make sure you've run this SQL on your PRODUCTION database:

```sql
ALTER TABLE datasets ALTER COLUMN user_id DROP NOT NULL;
```

This allows anonymous users to generate images without signing up.

---

## How It Works

### 1. Context Building

The endpoint builds a rich prompt by combining:

**Business Profile Context** (if user is logged in):
```
Brand: Coffee Shop. Vibe: cozy, warm. Theme: rustic.
```

**Dataset Style Guidelines** (if dataset_id provided):
```
Style Guidelines: Photorealistic, natural lighting, warm tones.
Reference style: bright, natural, cozy.
```

**User Prompt**:
```
a dog drinking coffee
```

**Final Prompt**:
```
Brand: Coffee Shop. Vibe: cozy, warm. Theme: rustic. Style Guidelines: Photorealistic, natural lighting, warm tones. Reference style: bright, natural, cozy. a dog drinking coffee Style: Photorealistic.
```

### 2. Image Generation

Uses Imagen 3 via Gemini API:
```python
model = genai.ImageGenerationModel("imagen-3.0-generate-001")
response = model.generate_images(
    prompt=full_prompt,
    number_of_images=1,
    aspect_ratio="1:1",  # or 16:9, 9:16, 4:3, 3:4
    safety_filter_level="block_some",
    person_generation="allow_adult"
)
```

### 3. Storage Upload

Generated image is uploaded to Supabase:
```python
file_path = f"generated/{uuid}.png"
supabase.storage.from_("generated-images").upload(
    path=file_path,
    file=image_bytes,
    file_options={"content-type": "image/png"}
)
```

### 4. Response

Returns the public URL:
```json
{
  "image_url": "https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/generated-images/generated/abc-123.png",
  "caption": "a dog drinking coffee",
  "prompt_used": "Brand: Coffee Shop...",
  "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
  "style": "Photorealistic",
  "aspect_ratio": "1:1"
}
```

---

## API Usage

### Request Format

```bash
POST /ai/generate
Content-Type: application/json
Authorization: Bearer <optional-jwt-token>

{
  "prompt": "a dog drinking coffee in a cozy shop",
  "style": "Photorealistic",
  "aspect_ratio": "1:1",
  "quality": "standard",
  "format": "png",
  "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a"
}
```

### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | ✅ Yes | - | The image description |
| `style` | string | ❌ No | - | Style hint (e.g., "Photorealistic", "Anime", "Oil Painting") |
| `aspect_ratio` | string | ❌ No | "1:1" | Image aspect ratio: "1:1", "16:9", "9:16", "4:3", "3:4" |
| `quality` | string | ❌ No | "standard" | Image quality (reserved for future use) |
| `format` | string | ❌ No | "png" | Output format: "png", "jpg", "webp" |
| `dataset_id` | string | ❌ No | - | Reference dataset for style guidelines |

### Response Format

**Success (200 OK):**
```json
{
  "image_url": "https://storage.url/path/to/image.png",
  "caption": "a dog drinking coffee",
  "prompt_used": "Full prompt with context...",
  "dataset_id": "uuid",
  "style": "Photorealistic",
  "aspect_ratio": "1:1"
}
```

**Error (400/500):**
```json
{
  "detail": "Error message explaining what went wrong"
}
```

---

## Testing

### 1. Test with curl (Anonymous)

```bash
curl -X POST https://ai-picture-apis.onrender.com/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a cute puppy playing in a park",
    "style": "Photorealistic",
    "aspect_ratio": "1:1"
  }'
```

### 2. Test with curl (Authenticated)

```bash
curl -X POST https://ai-picture-apis.onrender.com/ai/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "prompt": "a cute puppy playing in a park",
    "style": "Photorealistic",
    "aspect_ratio": "16:9",
    "dataset_id": "your-dataset-id"
  }'
```

### 3. Test with Dataset Context

```bash
curl -X POST https://ai-picture-apis.onrender.com/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a coffee cup on a wooden table",
    "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a"
  }'
```

---

## Pricing

**Imagen 3 Pricing:** $0.03 per image

**Estimated Monthly Costs:**
- 100 images/month: $3
- 1,000 images/month: $30
- 10,000 images/month: $300

**Note:** Make sure your Google Cloud billing is set up to avoid service interruptions.

---

## Features

### ✅ Implemented

1. **Imagen 3 Integration** - State-of-the-art image generation
2. **Business Profile Context** - Uses brand, vibe, and theme
3. **Dataset Style Guidelines** - References analyzed images for consistent style
4. **Multiple Aspect Ratios** - 1:1, 16:9, 9:16, 4:3, 3:4
5. **Supabase Storage** - Automatic upload and public URL generation
6. **Anonymous Support** - Works without authentication
7. **Error Handling** - Comprehensive error messages
8. **Logging** - Detailed logs for debugging

### 🔮 Future Enhancements

1. **Image Variations** - Generate multiple variations of the same prompt
2. **Image Editing** - Modify existing images with prompts
3. **Upscaling** - Generate higher resolution images
4. **Generation History** - Track user's generated images
5. **Favorites** - Save and organize favorite generations
6. **Batch Generation** - Generate multiple images at once
7. **Style Transfer** - Apply style from one image to another

---

## Troubleshooting

### Error: "Failed to upload image to storage"

**Solution:** Create the `generated-images` bucket in Supabase:
1. Go to Supabase dashboard → Storage
2. Create new bucket: `generated-images`
3. Make it public
4. Set the storage policies (see Setup section)

### Error: "No image generated by Imagen"

**Possible causes:**
- Prompt violates safety filters
- Google API quota exceeded
- Network timeout

**Solution:**
- Check Google Cloud Console for API errors
- Verify billing is enabled
- Try a different prompt

### Error: "Google API key not configured"

**Solution:** Make sure `GOOGLE_API_KEY` is set in your `.env` file:
```bash
GOOGLE_API_KEY="AIzaSyCbs1YgDMMmc1bvAgjtw_kh9aXj02gtZyk"
```

### Images not displaying in frontend

**Check:**
1. Is the `image_url` in the response valid?
2. Is the Supabase bucket public?
3. Are CORS settings correct on the bucket?
4. Can you access the URL directly in a browser?

---

## Code Changes Summary

### Files Modified:

1. **`app/routers/ai.py`**
   - Implemented full Imagen 3 image generation
   - Added dataset style reference extraction
   - Added Supabase storage upload
   - Returns proper `image_url` in response

2. **`requirements.txt`**
   - Added `pillow` for image processing

### New Features:

- ✅ Real image generation with Imagen 3
- ✅ Dataset style guidelines integration
- ✅ Business profile context integration
- ✅ Supabase storage upload
- ✅ Public URL generation
- ✅ Comprehensive error handling

---

## Next Steps

1. ✅ **Create the `generated-images` bucket** in Supabase
2. ✅ **Run the database migration** (make `datasets.user_id` nullable)
3. ✅ **Test the endpoint** with curl
4. ✅ **Test from frontend** - should work automatically now!
5. ⚠️ **Monitor costs** - Imagen 3 is $0.03 per image
6. ⚠️ **Set up rate limiting** - Prevent abuse
7. ⚠️ **Add usage tracking** - Monitor API usage per user

---

## Support

If you encounter any issues:
1. Check the server logs for detailed error messages
2. Verify all setup steps were completed
3. Test with curl first before testing from frontend
4. Check Supabase dashboard for storage issues
5. Verify Google Cloud billing is active

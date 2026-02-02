# Generated Images Tracking System

## Overview

All generated images are now tracked in the database with comprehensive metadata. Every time an image is generated, a record is created in the `generated_images` table storing the prompt, settings, and generation details.

## Database Schema

### Table: `generated_images`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key (auto-generated) |
| `user_id` | UUID | User who generated the image (nullable for anonymous) |
| `prompt` | TEXT | Original user prompt |
| `full_prompt` | TEXT | Complete prompt sent to AI (includes context) |
| `image_url` | TEXT | Public URL of generated image in storage |
| `dataset_id` | UUID | Associated dataset (if any) |
| `style` | TEXT | Style parameter used |
| `aspect_ratio` | TEXT | Aspect ratio (e.g., "1:1", "16:9") |
| `quality` | TEXT | Quality setting |
| `format` | TEXT | Image format (png, jpg, etc.) |
| `resolution` | TEXT | Resolution (1K, 2K, 4K) |
| `reference_images_count` | INTEGER | Number of reference images used |
| `unique_visual_elements` | JSONB | Array of visual elements from dataset |
| `created_at` | TIMESTAMPTZ | Generation timestamp |

### Indexes

- `idx_generated_images_user_id` - Fast lookup by user
- `idx_generated_images_dataset_id` - Fast lookup by dataset
- `idx_generated_images_created_at` - Chronological ordering

## API Endpoints

### 1. Generate Image (Enhanced)

**POST** `/ai/generate`

Now returns the generation record ID along with the image URL.

**Response:**
```json
{
  "id": "uuid-of-generation-record",
  "image_url": "https://...",
  "caption": "Original prompt",
  "prompt_used": "Full prompt with context",
  "dataset_id": "uuid-or-null",
  "style": "style-name",
  "aspect_ratio": "16:9",
  "quality": "standard",
  "format": "png",
  "resolution": "2K",
  "reference_images_count": 3
}
```

### 2. Get Generated Images History

**GET** `/ai/generated-images`

Retrieve all generated images with metadata.

**Query Parameters:**
- `limit` (default: 50) - Number of records to return
- `offset` (default: 0) - Pagination offset
- `dataset_id` (optional) - Filter by specific dataset

**Response:**
```json
{
  "images": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "prompt": "A modern coffee shop interior",
      "full_prompt": "Brand: Coffee Co. Vibe: cozy. UNIQUE ELEMENTS: wooden tables, pendant lights...",
      "image_url": "https://...",
      "dataset_id": "uuid",
      "style": "photorealistic",
      "aspect_ratio": "16:9",
      "quality": "standard",
      "format": "png",
      "resolution": "2K",
      "reference_images_count": 3,
      "unique_visual_elements": ["wooden tables", "pendant lights", "brick walls"],
      "created_at": "2026-02-02T10:30:00Z"
    }
  ],
  "count": 1,
  "offset": 0,
  "limit": 50
}
```

### 3. Get Generated Image by ID

**GET** `/ai/generated-images/{image_id}`

Retrieve a specific generated image record.

**Response:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "prompt": "A modern coffee shop interior",
  "full_prompt": "Brand: Coffee Co. Vibe: cozy. UNIQUE ELEMENTS: wooden tables...",
  "image_url": "https://...",
  "dataset_id": "uuid",
  "style": "photorealistic",
  "aspect_ratio": "16:9",
  "quality": "standard",
  "format": "png",
  "resolution": "2K",
  "reference_images_count": 3,
  "unique_visual_elements": ["wooden tables", "pendant lights", "brick walls"],
  "created_at": "2026-02-02T10:30:00Z"
}
```

## What Gets Tracked

### Always Tracked
- ✅ Original user prompt
- ✅ Full prompt sent to AI (with all context)
- ✅ Image URL in Supabase Storage
- ✅ Generation timestamp
- ✅ User ID (if authenticated, null for anonymous)

### Generation Settings
- ✅ Style parameter
- ✅ Aspect ratio
- ✅ Quality setting
- ✅ Image format
- ✅ Resolution (1K/2K/4K)

### Dataset Context (if used)
- ✅ Dataset ID
- ✅ Number of reference images used
- ✅ Unique visual elements extracted from dataset

## Benefits

1. **Full Audit Trail** - Every generation is tracked with complete metadata
2. **User History** - Users can see all their past generations
3. **Dataset Analytics** - Track which datasets are used most
4. **Prompt Analysis** - Analyze what prompts work best
5. **Cost Tracking** - Monitor generation volume per user
6. **Debugging** - Full context for troubleshooting issues

## Storage Architecture

### Supabase Storage Buckets
- `generated-images` - Stores actual image files
- Public access enabled for easy sharing

### Database Records
- `generated_images` table - Stores all metadata
- Links to storage via `image_url`
- Cascading delete on user deletion

## Usage Examples

### Frontend: Display User's Generation History

```javascript
const response = await fetch('/ai/generated-images?limit=20&offset=0', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const { images } = await response.json();

images.forEach(img => {
  console.log(`Prompt: ${img.prompt}`);
  console.log(`Image: ${img.image_url}`);
  console.log(`Generated: ${img.created_at}`);
});
```

### Frontend: Filter by Dataset

```javascript
const response = await fetch(`/ai/generated-images?dataset_id=${datasetId}`);
const { images } = await response.json();

// Show all images generated using this dataset
```

### Analytics: Most Used Visual Elements

```sql
SELECT 
  jsonb_array_elements_text(unique_visual_elements) as element,
  COUNT(*) as usage_count
FROM generated_images
WHERE unique_visual_elements IS NOT NULL
GROUP BY element
ORDER BY usage_count DESC
LIMIT 10;
```

## Migration Notes

- ✅ Table created with proper indexes
- ✅ Foreign keys to `auth.users` and `datasets`
- ✅ Cascading delete on user deletion
- ✅ SET NULL on dataset deletion (preserves generation history)
- ✅ Works for both authenticated and anonymous users

## Anonymous Users

Anonymous users (free tier) can still generate images:
- `user_id` is stored as NULL
- All other metadata is tracked normally
- Images are still saved to storage
- No filtering by user in history endpoint

## Next Steps

Consider adding:
1. **Favorites** - Let users mark favorite generations
2. **Regenerate** - Endpoint to regenerate from saved prompt
3. **Analytics Dashboard** - Visualize generation trends
4. **Export** - Download generation history as CSV
5. **Search** - Full-text search on prompts

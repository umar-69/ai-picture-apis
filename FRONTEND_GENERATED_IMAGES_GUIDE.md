# Frontend Integration Guide: Generated Images Tracking

## Overview

The `/ai/generate` endpoint now returns a generation ID and stores complete metadata in the database. You can retrieve generation history and individual records.

## Quick Start

### 1. Generate Image (Enhanced Response)

**Endpoint:** `POST /ai/generate`

**Request:**
```javascript
const response = await fetch('/ai/generate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}` // Optional for free tier
  },
  body: JSON.stringify({
    prompt: "Modern coffee shop interior with wooden tables",
    style: "photorealistic",
    aspect_ratio: "16:9",
    quality: "standard",
    format: "png",
    dataset_id: "uuid-of-dataset" // Optional
  })
});

const data = await response.json();
```

**Response (NEW - includes generation ID):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "image_url": "https://your-supabase.storage.co/generated-images/generated-uuid.png",
  "caption": "Modern coffee shop interior with wooden tables",
  "prompt_used": "Brand: Coffee Co. Vibe: cozy. UNIQUE ELEMENTS: wooden tables, pendant lights. SCENE: Modern coffee shop interior with wooden tables",
  "dataset_id": "dataset-uuid-or-null",
  "style": "photorealistic",
  "aspect_ratio": "16:9",
  "quality": "standard",
  "format": "png",
  "resolution": "2K",
  "reference_images_count": 3
}
```

**What's New:**
- ✅ `id` - Database record ID for this generation
- ✅ `quality`, `format`, `resolution` - Generation settings
- ✅ `reference_images_count` - How many dataset images were used

### 2. Get User's Generation History

**Endpoint:** `GET /ai/generated-images`

**Request:**
```javascript
const response = await fetch('/ai/generated-images?limit=20&offset=0', {
  headers: {
    'Authorization': `Bearer ${token}` // Optional - filters by user if provided
  }
});

const data = await response.json();
```

**Query Parameters:**
- `limit` (default: 50) - Number of records per page
- `offset` (default: 0) - Pagination offset
- `dataset_id` (optional) - Filter by specific dataset

**Response:**
```json
{
  "images": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "user-uuid-or-null",
      "prompt": "Modern coffee shop interior",
      "full_prompt": "Brand: Coffee Co. Vibe: cozy. UNIQUE ELEMENTS: wooden tables...",
      "image_url": "https://...",
      "dataset_id": "dataset-uuid-or-null",
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

### 3. Get Specific Generation by ID

**Endpoint:** `GET /ai/generated-images/{id}`

**Request:**
```javascript
const generationId = "550e8400-e29b-41d4-a716-446655440000";
const response = await fetch(`/ai/generated-images/${generationId}`, {
  headers: {
    'Authorization': `Bearer ${token}` // Optional
  }
});

const generation = await response.json();
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-uuid",
  "prompt": "Modern coffee shop interior",
  "full_prompt": "Brand: Coffee Co. Vibe: cozy...",
  "image_url": "https://...",
  "dataset_id": "dataset-uuid",
  "style": "photorealistic",
  "aspect_ratio": "16:9",
  "quality": "standard",
  "format": "png",
  "resolution": "2K",
  "reference_images_count": 3,
  "unique_visual_elements": ["wooden tables", "pendant lights"],
  "created_at": "2026-02-02T10:30:00Z"
}
```

## UI Implementation Examples

### Example 1: Display Generation History

```javascript
async function loadGenerationHistory() {
  const response = await fetch('/ai/generated-images?limit=20&offset=0', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const { images } = await response.json();
  
  // Render images in gallery
  const gallery = document.getElementById('gallery');
  images.forEach(img => {
    gallery.innerHTML += `
      <div class="generation-card">
        <img src="${img.image_url}" alt="${img.prompt}" />
        <div class="meta">
          <p class="prompt">${img.prompt}</p>
          <p class="date">${new Date(img.created_at).toLocaleDateString()}</p>
          <p class="settings">${img.resolution} • ${img.aspect_ratio}</p>
          ${img.dataset_id ? '<span class="badge">Dataset Used</span>' : ''}
        </div>
      </div>
    `;
  });
}
```

### Example 2: Pagination

```javascript
function GenerationHistory() {
  const [page, setPage] = useState(0);
  const [images, setImages] = useState([]);
  const limit = 20;
  
  useEffect(() => {
    async function load() {
      const offset = page * limit;
      const res = await fetch(`/ai/generated-images?limit=${limit}&offset=${offset}`);
      const data = await res.json();
      setImages(data.images);
    }
    load();
  }, [page]);
  
  return (
    <div>
      <div className="gallery">
        {images.map(img => (
          <ImageCard key={img.id} image={img} />
        ))}
      </div>
      <Pagination 
        page={page} 
        onNext={() => setPage(p => p + 1)}
        onPrev={() => setPage(p => Math.max(0, p - 1))}
      />
    </div>
  );
}
```

### Example 3: Filter by Dataset

```javascript
async function loadDatasetGenerations(datasetId) {
  const response = await fetch(
    `/ai/generated-images?dataset_id=${datasetId}&limit=50`
  );
  
  const { images } = await response.json();
  
  return images; // All generations using this dataset
}
```

### Example 4: Regenerate from History

```javascript
async function regenerateImage(generationId) {
  // 1. Fetch the original generation
  const response = await fetch(`/ai/generated-images/${generationId}`);
  const original = await response.json();
  
  // 2. Use the same settings to regenerate
  const regenerateResponse = await fetch('/ai/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt: original.prompt,
      style: original.style,
      aspect_ratio: original.aspect_ratio,
      quality: original.quality,
      format: original.format,
      dataset_id: original.dataset_id
    })
  });
  
  const newGeneration = await regenerateResponse.json();
  return newGeneration;
}
```

### Example 5: Show Full Prompt Details

```javascript
function GenerationDetails({ generationId }) {
  const [generation, setGeneration] = useState(null);
  
  useEffect(() => {
    fetch(`/ai/generated-images/${generationId}`)
      .then(res => res.json())
      .then(setGeneration);
  }, [generationId]);
  
  if (!generation) return <Loading />;
  
  return (
    <div className="details">
      <img src={generation.image_url} alt={generation.prompt} />
      
      <div className="metadata">
        <h3>Your Prompt</h3>
        <p>{generation.prompt}</p>
        
        <h3>Full AI Prompt</h3>
        <p className="full-prompt">{generation.full_prompt}</p>
        
        <h3>Settings</h3>
        <ul>
          <li>Style: {generation.style}</li>
          <li>Aspect Ratio: {generation.aspect_ratio}</li>
          <li>Resolution: {generation.resolution}</li>
          <li>Quality: {generation.quality}</li>
        </ul>
        
        {generation.unique_visual_elements && (
          <>
            <h3>Visual Elements Used</h3>
            <div className="tags">
              {generation.unique_visual_elements.map(element => (
                <span key={element} className="tag">{element}</span>
              ))}
            </div>
          </>
        )}
        
        {generation.reference_images_count > 0 && (
          <p className="info">
            Generated using {generation.reference_images_count} reference images
          </p>
        )}
      </div>
    </div>
  );
}
```

## Data Structure Reference

### Generation Record Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique generation ID |
| `user_id` | UUID/null | User who generated (null for anonymous) |
| `prompt` | string | Original user prompt |
| `full_prompt` | string | Complete prompt sent to AI |
| `image_url` | string | Public URL of generated image |
| `dataset_id` | UUID/null | Associated dataset |
| `style` | string | Style parameter |
| `aspect_ratio` | string | e.g., "16:9", "1:1" |
| `quality` | string | e.g., "standard", "high" |
| `format` | string | e.g., "png", "jpg" |
| `resolution` | string | e.g., "1K", "2K", "4K" |
| `reference_images_count` | number | Number of reference images used |
| `unique_visual_elements` | array | Visual elements from dataset |
| `created_at` | ISO 8601 | Generation timestamp |

## Common Use Cases

### 1. User Profile - "My Generations"
Show all images a user has generated with pagination.

### 2. Dataset Page - "Generated with this Dataset"
Show all images generated using a specific dataset.

### 3. Image Details Modal
Display full generation metadata when user clicks an image.

### 4. Regenerate Button
Allow users to regenerate an image with the same settings.

### 5. Export History
Download user's generation history as JSON/CSV.

### 6. Analytics Dashboard
Show generation trends, popular prompts, dataset usage.

## Error Handling

```javascript
async function generateImage(prompt) {
  try {
    const response = await fetch('/ai/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    // Save generation ID for later reference
    localStorage.setItem('lastGenerationId', data.id);
    
    return data;
  } catch (error) {
    console.error('Generation failed:', error);
    throw error;
  }
}
```

## TypeScript Types

```typescript
interface GeneratedImage {
  id: string;
  user_id: string | null;
  prompt: string;
  full_prompt: string;
  image_url: string;
  dataset_id: string | null;
  style: string | null;
  aspect_ratio: string | null;
  quality: string | null;
  format: string | null;
  resolution: string | null;
  reference_images_count: number;
  unique_visual_elements: string[] | null;
  created_at: string; // ISO 8601
}

interface GenerationHistoryResponse {
  images: GeneratedImage[];
  count: number;
  offset: number;
  limit: number;
}

interface GenerateImageResponse {
  id: string;
  image_url: string;
  caption: string;
  prompt_used: string;
  dataset_id: string | null;
  style: string | null;
  aspect_ratio: string;
  quality: string;
  format: string;
  resolution: string;
  reference_images_count: number;
}
```

## Notes

- **Anonymous Users:** Can generate images but won't see history (no user_id)
- **Authentication:** Optional for generation, but required to filter history by user
- **Pagination:** Use `offset` and `limit` for large result sets
- **Timestamps:** All in UTC, format as ISO 8601
- **Image URLs:** Public, no authentication needed to view
- **Cascading Deletes:** If user is deleted, their generation records are deleted too

## Migration Impact

**Breaking Changes:** None! The API is backward compatible.

**New Features:**
- ✅ Generation ID returned in `/ai/generate` response
- ✅ New endpoints for history retrieval
- ✅ More metadata in responses

**Existing Code:** Will continue to work. The `image_url` field is still returned as before.

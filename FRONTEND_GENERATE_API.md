# Image Generation API Guide for Frontend

This guide documents the updated `POST /ai/generate` endpoint for generating brand-aligned images.

## Endpoint

**POST** `/ai/generate`

Generates a high-quality image using your brand's visual DNA. The system automatically selects up to 14 most relevant reference images from the specified folder based on the user's prompt and style (using semantic ranking over analyzed image metadata).

### Authentication

Requires a Bearer token in the header (if user is logged in). Also works for unauthenticated users (if configured), but they won't have credit tracking.

```javascript
headers: {
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>" 
}
```

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | **Yes** | The description of the scene you want to generate (e.g., "Latte on a marble table"). |
| `folder_id` | UUID | **Yes** | The ID of the dataset/folder containing reference images. |
| `dataset_id` | UUID | No | Alias for `folder_id`. Use `folder_id` if possible. |
| `image_style` | string | No | The visual style. Default: `photorealistic`. Options: `photorealistic`, `cinematic`, `illustration`, `3d_render`, `minimalist`. |
| `aspect_ratio` | string | No | Default: `1:1`. Options: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`. |
| `quality` | string | No | Default: `standard`. |
| `format` | string | No | Output format. Default: `png`. |

### Example Request

```json
{
  "prompt": "Morning coffee and pastries on a wooden board with soft natural light, relaxed cafe vibe",
  "folder_id": "4375cd45-c454-4936-a10b-3daea640d973",
  "image_style": "photorealistic",
  "aspect_ratio": "1:1"
}
```

### Response

Returns the generated image URL and metadata.

**Success (200 OK):**

```json
{
  "id": "d6a1e87c-9e4c-40b8-8dee-0fbaa61af75f",
  "image_url": "https://your-project.supabase.co/storage/v1/object/public/generated-images/generated/img-123.png",
  "caption": "Morning coffee and pastries...",
  "prompt_used": "Full system prompt used...",
  "dataset_id": "4375cd45-c454-4936-a10b-3daea640d973",
  "folder_id": "4375cd45-c454-4936-a10b-3daea640d973",
  "image_style": "photorealistic",
  "reference_images_count": 14,
  "credits_used": 5
}
```

### Error Responses

- **400 Bad Request**: Missing required fields.
- **502 Bad Gateway**: Generation failed (e.g. content policy). The error message will suggest trying a simpler prompt.
- **503 Service Unavailable**: Temporary AI service outage.

---

## Integration Code (React/JavaScript Example)

```javascript
const generateImage = async (prompt, folderId) => {
  try {
    const response = await fetch('https://your-api-url.com/ai/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` // if authenticated
      },
      body: JSON.stringify({
        prompt: prompt,
        folder_id: folderId,
        image_style: "photorealistic",
        aspect_ratio: "1:1"
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Generation failed');
    }

    const data = await response.json();
    console.log("Generated Image URL:", data.image_url);
    return data;

  } catch (error) {
    console.error("Error generating image:", error);
    alert(error.message);
  }
};
```

## Important Notes for Frontend

1.  **Loading State**: Generation typically takes **40-60 seconds**.
    -   *Recommendation*: Show a progress bar or a skeleton loader.
    -   *Do not* timeout the request on the client side before 90s.

2.  **Smart Selection**: You don't need to pass image URLs.
    -   The backend automatically scans **all images** in the `folder_id` you provide.
    -   It picks the top 5 matches based on the user's `prompt`.
    -   Example: If the prompt mentions "coffee", it automatically finds coffee-related images from the brand folder.

3.  **Reliability**:
    -   The API now has built-in retry logic. If a generation fails (e.g. "payload too large"), it automatically retries with fewer reference images.
    -   You might see a slightly longer response time (e.g. 70s) if a retry happened, but it ensures a successful result.

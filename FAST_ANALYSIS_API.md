# ⚡️ Fast Image Analysis API

This endpoint is designed for high-speed, parallel analysis of large batches of images using **Gemini 3.0 Flash**. It is significantly faster than the standard upload-and-analyze flow and is optimized for processing images that are already stored in Supabase.

## Endpoint

`POST /ai/dataset/analyze-fast`

### Headers
- `Content-Type: application/json`
- `Authorization: Bearer <token>` (Optional, but recommended for user tracking)

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dataset_id` | `string` | Yes | The UUID of the dataset to associate these images with. |
| `image_urls` | `string[]` | Yes | An array of public URLs for the images to analyze. |

**Example Request:**

```json
{
  "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
  "image_urls": [
    "https://your-project.supabase.co/storage/v1/object/public/dataset-images/img1.jpg",
    "https://your-project.supabase.co/storage/v1/object/public/dataset-images/img2.jpg",
    "https://your-project.supabase.co/storage/v1/object/public/dataset-images/img3.jpg"
  ]
}
```

---

## Response

The API returns a JSON object containing the analysis results for each successfully processed image.

| Field | Type | Description |
|-------|------|-------------|
| `results` | `array` | List of analysis objects (see below). |
| `total_processed` | `integer` | Total number of URLs received. |
| `successful` | `integer` | Number of images successfully analyzed. |

### Result Object Structure

Each item in the `results` array contains:

- `dataset_id`: The ID of the dataset.
- `image_url`: The URL of the analyzed image.
- `analysis_result`: The AI-generated metadata.
  - `description`: Brief description highlighting unique design features.
  - `tags`: **Exactly 5 specific visual elements** (e.g., 'Marble Countertop', 'Warm Neon', 'Industrial Pipes', 'Exposed Brick', 'Edison Bulbs').
  - `lighting`: Specific lighting type and characteristics.
  - `colors`: Dominant colors or materials.
  - `vibe`: Overall mood and atmosphere.

**Example Response:**

```json
{
  "results": [
    {
      "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
      "image_url": "https://your-project.supabase.co/storage/v1/object/public/dataset-images/img1.jpg",
      "analysis_result": {
        "description": "Cafe scene featuring artisan pastries on rustic wooden board atop marble table with gold veining",
        "tags": [
          "Black Marble Table",
          "Checkered Woven Chairs",
          "Artisan Pastries",
          "Latte Art",
          "Gold Veining"
        ],
        "lighting": "Soft diffused natural lighting with gentle shadows",
        "colors": [
          "Black Marble",
          "Gold Accents",
          "Cream Checkered Pattern",
          "Golden Brown Pastries"
        ],
        "vibe": "Sophisticated, cozy, and indulgent."
      },
      "created_at": "2026-02-01T21:57:22.603517+00:00"
    }
  ],
  "total_processed": 1,
  "successful": 1
}
```

---

## Integration Notes

1.  **Performance:** This endpoint processes images in parallel (up to 10 concurrently). It is ideal for "bulk analyze" features.
2.  **Storage:** Images **must** be accessible via the provided URLs (e.g., public Supabase Storage URLs). The API downloads them temporarily to send to the AI model.
3.  **Database:** Results are automatically saved to the `dataset_images` table in Supabase. You do not need to make a separate DB call to save the analysis.

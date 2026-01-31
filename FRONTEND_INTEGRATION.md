# Frontend Integration Guide: Image Upload & Analysis

This guide details the changes required in the frontend application to integrate with the new backend image analysis workflow.

## Overview

The backend has been updated to support direct file uploads. Instead of converting images to Base64 strings, you should now send `File` objects directly using `FormData`. The backend handles uploading these files to Supabase Storage and storing the analysis results in the database.

## 1. Upload & Analyze Images

**URL**: `/ai/dataset/analyze`
**Method**: `POST`
**Content-Type**: `multipart/form-data`

### Request Body

| Field | Type | Description |
|-------|------|-------------|
| `dataset_id` | `string` | The UUID of the dataset these images belong to. |
| `files` | `File[]` | One or more image files to upload and analyze. |

### Example Request (JavaScript/TypeScript)

```typescript
async function uploadAndAnalyzeImages(datasetId: string, files: File[]) {
  const formData = new FormData();
  
  // Append the dataset ID
  formData.append('dataset_id', datasetId);
  
  // Append each file. Note: The field name must be 'files' (plural)
  files.forEach((file) => {
    formData.append('files', file);
  });

  try {
    const response = await fetch('https://ai-picture-apis.onrender.com/ai/dataset/analyze', {
      method: 'POST',
      headers: {
        // Authorization header is required. 
        // Get this from `supabase.auth.getSession()` -> `session.access_token`
        'Authorization': `Bearer ${session.access_token}`, 
        // Do NOT set 'Content-Type': 'multipart/form-data' manually!
        // The browser sets it automatically with the correct boundary.
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    const data = await response.json();
    return data.results; // Returns array of created dataset_images records
  } catch (error) {
    console.error('Upload failed:', error);
    throw error;
  }
}
```

### Response Format

The API returns a JSON object containing the results of the operation.

```json
{
  "results": [
    {
      "id": "uuid-of-record",
      "dataset_id": "uuid-of-dataset",
      "image_url": "https://.../dataset-images/uuid.jpg",
      "analysis_result": {
        "description": "...",
        "tags": ["..."]
      },
      "created_at": "timestamp"
    }
    // ... more results
  ]
}
```

## 2. Fetch Dataset Images & Analysis

**URL**: `/ai/dataset/{dataset_id}/images`
**Method**: `GET`
**Auth**: Optional (Supports anonymous users for free tries)

Use this endpoint to retrieve all images uploaded to a dataset along with their AI-generated analysis (tags, description, style).

### Example Request

```typescript
async function getDatasetImages(datasetId: string) {
  try {
    const response = await fetch(`https://ai-picture-apis.onrender.com/ai/dataset/${datasetId}/images`, {
      method: 'GET',
      headers: {
        // Optional: Include token if user is logged in
        // 'Authorization': `Bearer ${session.access_token}`
      }
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    const data = await response.json();
    return data.images;
  } catch (error) {
    console.error('Fetch failed:', error);
    throw error;
  }
}
```

### Response Format

```json
{
  "images": [
    {
      "id": "uuid-of-record",
      "dataset_id": "uuid-of-dataset",
      "image_url": "https://supabasestorage.com/.../image.jpg",
      "analysis_result": {
        "description": "A detailed description of the image content and style.",
        "tags": ["modern", "minimalist", "warm lighting"],
        "lighting": "Natural sunlight",
        "colors": ["#FFFFFF", "#FF5733"],
        "vibe": "Professional and clean"
      },
      "created_at": "2024-01-30T12:00:00Z"
    }
  ]
}
```

## 3. Generate Images (Nano Banana Pro)

**URL**: `/ai/generate`
**Method**: `POST`
**Content-Type**: `application/json`

Generate professional-quality images using Gemini 3 Pro Image Preview (Nano Banana Pro). This endpoint supports style consistency by using your dataset images as visual context.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | `string` | Yes | The text prompt describing the image you want to generate. |
| `dataset_id` | `string` | No | The UUID of an analyzed dataset. If provided, the API will use up to 5 images from this dataset as visual reference to match the style. |
| `aspect_ratio` | `string` | No | The desired aspect ratio. Defaults to "1:1". Supported: "1:1", "16:9", "9:16", "4:3", "3:4", "2:3", "3:2", "4:5", "5:4", "21:9". |
| `style` | `string` | No | Optional style keyword (e.g., "Photorealistic", "Cinematic", "Minimalist"). |

### Example Request

```typescript
async function generateImage(prompt: string, datasetId?: string) {
  try {
    const response = await fetch('https://ai-picture-apis.onrender.com/ai/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // 'Authorization': `Bearer ${token}` // Optional
      },
      body: JSON.stringify({
        prompt: prompt,
        dataset_id: datasetId, // Optional: Uses dataset images for style matching
        aspect_ratio: "1:1",
        style: "Photorealistic"
      }),
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    const data = await response.json();
    return data; // Contains image_url
  } catch (error) {
    console.error('Generation failed:', error);
    throw error;
  }
}
```

### Response Format

```json
{
  "image_url": "https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/generated-images/generated/abc-123.png",
  "caption": "a latte with latte art",
  "prompt_used": "Style Guidelines: ... Match the style and aesthetic of the 5 reference image(s) provided. a latte with latte art",
  "dataset_id": "uuid-of-dataset",
  "style": "Photorealistic",
  "aspect_ratio": "1:1"
}
```

### Key Features
- **Visual Style Matching**: If `dataset_id` is provided, the API downloads actual images from your dataset and passes them to the AI to replicate the lighting, colors, and vibe.
- **High Resolution**: Generates 2K resolution images by default.
- **Advanced Reasoning**: Uses Gemini 3 Pro's "Thinking" mode for better prompt adherence.

## Migration Steps for `src/routes/image/+page.svelte`

1.  **Remove Base64 Conversion**: Delete the code that uses `FileReader` to convert images to data URLs (`data:image/jpeg;base64...`).
2.  **Store File Objects**: Update your state to store the original `File` objects returned from the file input.
3.  **Update API Call**: Replace the call to `analyzeImagesWithGemini` with the new `uploadAndAnalyzeImages` function (or equivalent logic) shown above.
4.  **Handle Response**: The response now contains the permanent URL (`image_url`) and the analysis. Update your UI to display these.
5.  **Display Analysis**: Use the `analysis_result` object to show tags, descriptions, and other style info on the frontend.
6.  **Integrate Generation**: Add a form or button to call `generateImage` using the `dataset_id` returned from the analysis step.

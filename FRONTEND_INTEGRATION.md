# Frontend Integration Guide: Image Upload & Analysis

This guide details the changes required in the frontend application to integrate with the new backend image analysis workflow.

## Overview

The backend has been updated to support direct file uploads. Instead of converting images to Base64 strings, you should now send `File` objects directly using `FormData`. The backend handles uploading these files to Supabase Storage and storing the analysis results in the database.

## New API Endpoint

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

## Migration Steps for `src/routes/image/+page.svelte`

1.  **Remove Base64 Conversion**: Delete the code that uses `FileReader` to convert images to data URLs (`data:image/jpeg;base64...`).
2.  **Store File Objects**: Update your state to store the original `File` objects returned from the file input.
3.  **Update API Call**: Replace the call to `analyzeImagesWithGemini` with the new `uploadAndAnalyzeImages` function (or equivalent logic) shown above.
4.  **Handle Response**: The response now contains the permanent URL (`image_url`) and the analysis. Update your UI to display these.

## Database Changes (Backend)

The backend now writes to a new table `dataset_images` in Supabase:
- `dataset_id`: Links to your dataset.
- `image_url`: Public URL of the uploaded image.
- `analysis_result`: JSON field containing AI analysis.

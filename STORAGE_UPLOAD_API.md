# 📤 Storage Upload API (Anonymous-Friendly)

These endpoints allow uploading images to Supabase Storage without authentication, perfect for the free tier workflow.

---

## Single File Upload

`POST /storage/upload`

### Headers
- `Content-Type: multipart/form-data`
- `Authorization: Bearer <token>` (Optional - works without auth for free tier)

### Request Body (Form Data)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | `File` | Yes | The image file to upload |
| `dataset_id` | `string` | No | Dataset UUID (if omitted, uploads to "temp" folder) |

**Example Request (JavaScript/Fetch):**

```javascript
const formData = new FormData();
formData.append('file', imageFile);
formData.append('dataset_id', 'your-dataset-uuid');

const response = await fetch('/storage/upload', {
  method: 'POST',
  body: formData
});

const result = await response.json();
```

### Response

```json
{
  "file_path": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/abc123.jpg",
  "public_url": "https://your-project.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/abc123.jpg"
}
```

---

## Multiple Files Upload

`POST /storage/upload-multiple`

### Headers
- `Content-Type: multipart/form-data`
- `Authorization: Bearer <token>` (Optional)

### Request Body (Form Data)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | `File[]` | Yes | Array of image files to upload |
| `dataset_id` | `string` | No | Dataset UUID (if omitted, uploads to "temp" folder) |

**Example Request (JavaScript/Fetch):**

```javascript
const formData = new FormData();
imageFiles.forEach(file => {
  formData.append('files', file);
});
formData.append('dataset_id', 'your-dataset-uuid');

const response = await fetch('/storage/upload-multiple', {
  method: 'POST',
  body: formData
});

const result = await response.json();
```

### Response

```json
{
  "files": [
    {
      "file_path": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/abc123.jpg",
      "public_url": "https://your-project.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/abc123.jpg",
      "filename": "image1.jpg"
    },
    {
      "file_path": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/def456.jpg",
      "public_url": "https://your-project.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/def456.jpg",
      "filename": "image2.jpg"
    }
  ],
  "count": 2
}
```

---

## Complete Workflow: Upload + Analyze

For the free tier "quick analysis" feature, use this two-step workflow:

### Step 1: Upload Images

```javascript
// Upload multiple images
const formData = new FormData();
selectedImages.forEach(file => {
  formData.append('files', file);
});
formData.append('dataset_id', datasetId);

const uploadResponse = await fetch('/storage/upload-multiple', {
  method: 'POST',
  body: formData
});

const { files } = await uploadResponse.json();
const imageUrls = files.map(f => f.public_url);
```

### Step 2: Analyze Images

```javascript
// Analyze the uploaded images
const analysisResponse = await fetch('/ai/dataset/analyze-fast', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    dataset_id: datasetId,
    image_urls: imageUrls
  })
});

const { results } = await analysisResponse.json();
```

---

## Notes

1. **Anonymous Access:** Both endpoints work without authentication for free tier users.
2. **Storage Bucket:** Files are uploaded to the `dataset-images` bucket in Supabase.
3. **File Organization:** Files are organized by `dataset_id` or placed in a `temp` folder.
4. **Public URLs:** All uploaded files get public URLs immediately (no signed URLs needed).

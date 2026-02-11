# Image Style & Universal Analysis API — Frontend Integration

This document describes the **image analysis** and **image generation** API changes for universal datasets and the new **image style** option. Use it to integrate the frontend with the updated backend.

---

## Table of Contents

1. [Overview](#overview)
2. [Image Analysis — New Response Shape](#image-analysis--new-response-shape)
3. [Analyze Dataset (Upload) — `POST /ai/dataset/analyze`](#analyze-dataset-upload--post-aidatasetanalyze)
4. [Analyze Dataset (Fast) — `POST /ai/dataset/analyze-fast`](#analyze-dataset-fast--post-aidatasetanalyze-fast)
5. [Generate Image — `POST /ai/generate`](#generate-image--post-aigenerate)
6. [Image Style Values Reference](#image-style-values-reference)
7. [Generated Images List & Detail](#generated-images-list--detail)
8. [Example Frontend Flows](#example-frontend-flows)

---

## Overview

- **Analysis** is now **universal**: it works for any image type (food, fashion, interiors, products, portraits, landscapes, etc.), not just coffee shops. Each analyzed image returns `theme`, `image_style`, `key_elements`, plus existing `description`, `tags`, `lighting`, `colors`, `vibe`.
- **Generation** accepts an optional **`image_style`** from the frontend. The user can choose how the image should look (e.g. photorealistic, cinematic, illustration). If not set, the backend uses the dataset’s dominant style or defaults to `photorealistic`.
- **`image_style`** is stored on each generation and returned in list/detail so the UI can show “Style: cinematic” etc.

---

## Image Analysis — New Response Shape

Analysis results are stored in `dataset_images.analysis_result` (JSONB) and returned when you fetch dataset images or call analyze endpoints.

### Analysis result object (per image)

| Field           | Type     | Description |
|----------------|----------|-------------|
| `description`  | string   | Detailed description of content, composition, setting, textures, materials. |
| `tags`         | string[] | 8–12 keywords: subject, materials, style, distinctive features. |
| `lighting`     | string   | Type (natural/studio/neon/mixed), direction, quality, color temperature. |
| `colors`       | string or array | 3–6 dominant colors/tones (e.g. `"warm amber"`, `"matte black"`). |
| `vibe`         | string   | Overall mood (e.g. `"cozy and intimate"`, `"clean and professional"`). |
| `theme`        | string   | **New.** Broad category: e.g. `"interior design"`, `"food photography"`, `"portrait"`, `"product shot"`, `"landscape"`. |
| `image_style`  | string   | **New.** One of the [image style values](#image-style-values-reference) (e.g. `"photorealistic"`, `"cinematic"`). |
| `key_elements` | string[] | **New.** 3–5 most important visual elements that define the image. |

Example:

```json
{
  "description": "Modern café interior with exposed brick, marble counter, pendant lights.",
  "tags": ["Exposed Brick", "Marble Counter", "Pendant Lights", "Warm Ambient", "Shallow Depth of Field"],
  "lighting": "Warm ambient and pendant, soft diffused, front-lit",
  "colors": ["warm amber", "matte black", "cream", "copper"],
  "vibe": "cozy and intimate",
  "theme": "interior design",
  "image_style": "photorealistic",
  "key_elements": ["Exposed brick wall", "Marble countertop", "Pendant lighting", "Wooden stools"]
}
```

Use `theme` and `image_style` in the UI (e.g. badges, filters). Use `key_elements` and `tags` for search or “replicate this look” hints.

---

## Analyze Dataset (Upload) — `POST /ai/dataset/analyze`

Uploads images, runs universal analysis, and saves to the dataset.

### Request

- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Body:**
  - `dataset_id` or `datasetId` (string, required)
  - `files` (array of image files, required)

### Response

- **Success:** `200`
- **Body:**
  - `results`: array of created `dataset_images` rows (each includes `id`, `dataset_id`, `image_url`, `analysis_result` with the [new shape](#image-analysis--new-response-shape))
  - `credits_used`: number (if user logged in)

### Frontend usage

- After upload, read `results[].analysis_result.theme`, `analysis_result.image_style`, `analysis_result.key_elements` to show per-image metadata or to prefill a “style” selector for generation.

---

## Analyze Dataset (Fast) — `POST /ai/dataset/analyze-fast`

Same analysis contract as above, but accepts image URLs and processes in parallel. Response shape for each analyzed image is the same.

### Request

- **Method:** `POST`
- **Content-Type:** `application/json`
- **Body:**
  ```json
  {
    "dataset_id": "uuid-of-dataset",
    "image_urls": ["https://...", "https://..."]
  }
  ```

### Response

- **Success:** `200`
- **Body:**
  - `results`: array of created rows (each with `analysis_result` in the [new shape](#image-analysis--new-response-shape))
  - `total_processed`: number of URLs sent
  - `successful`: number of images successfully analyzed
  - `credits_used`: number (if user logged in)

---

## Generate Image — `POST /ai/generate`

Generates an image using the user’s prompt and optional **image style** and dataset/folder context.

### Request

- **Method:** `POST`
- **Content-Type:** `application/json`
- **Body (JSON):**

| Field             | Type   | Required | Description |
|-------------------|--------|----------|-------------|
| `prompt`          | string | Yes      | What to generate (e.g. “A cozy reading nook with warm light”). |
| `style`           | string | No       | Free-form style notes (e.g. “moody, evening”). |
| **`image_style`** | string | No       | **New.** Visual style. One of [image style values](#image-style-values-reference). If omitted: use dataset’s dominant style, or `photorealistic`. |
| `aspect_ratio`    | string | No       | Default `"1:1"`. Other options: `"16:9"`, `"9:16"`, `"4:3"`, `"3:4"`, `"2:3"`, `"3:2"`, `"4:5"`, `"5:4"`, `"21:9"`. |
| `quality`         | string | No       | Default `"standard"`. |
| `format`          | string | No       | Default `"png"`. |
| `dataset_id`      | string | No       | Dataset UUID for reference images and style. |
| `folder_id`       | string | No       | Folder (dataset) when using @-mention. |
| `environment_id`  | string | No       | Environment UUID for broad brand context. |

Example with style selection:

```json
{
  "prompt": "A cozy reading nook with warm light and plants",
  "image_style": "cinematic",
  "aspect_ratio": "16:9",
  "folder_id": "optional-dataset-uuid"
}
```

### Response

- **Success:** `200`
- **Body (relevant fields):**

| Field                    | Type   | Description |
|--------------------------|--------|-------------|
| `id`                     | string | Generated image record ID. |
| `image_url`              | string | Public URL of the generated image. |
| `caption`                | string | Same as `prompt`. |
| `prompt_used`            | string | Full prompt sent to the model (including style). |
| `dataset_id`             | string | Dataset used, if any. |
| `environment_id`         | string | Environment used, if any. |
| `folder_id`              | string | Folder used, if any. |
| `style`                  | string | Free-form style from request. |
| **`image_style`**        | string | **New.** Style actually used (user choice or dataset default). |
| `aspect_ratio`           | string | Aspect ratio used. |
| `quality`                | string | Quality used. |
| `format`                 | string | Format used. |
| `resolution`             | string | e.g. `"2K"`. |
| `reference_images_count` | number | Number of reference images used. |
| `credits_used`           | number | Credits deducted (0 if anonymous). |

### Style priority

1. **User choice:** `request.image_style` (from your dropdown).
2. **Dataset:** Dominant `image_style` from analyzed images in the selected dataset/folder.
3. **Default:** `"photorealistic"`.

---

## Image Style Values Reference

Use these exact strings in the **Image Style** dropdown and in `POST /ai/generate` → `image_style`.

| Value             | Brief description for UI |
|-------------------|---------------------------|
| `photorealistic`  | Photorealistic, true-to-life photo |
| `cinematic`       | Cinematic, film-like look |
| `illustration`    | Hand-drawn illustration |
| `graphic_design`  | Clean graphic / flat design |
| `3d_render`       | 3D rendered look |
| `watercolor`      | Watercolor painting |
| `oil_painting`    | Oil painting style |
| `sketch`          | Pencil/pen sketch |
| `pixel_art`       | Retro pixel art |
| `anime`           | Anime / manga style |
| `vintage_film`     | Vintage film photo |
| `documentary`     | Documentary-style photo |
| `editorial`       | Editorial / magazine style |
| `studio_product`  | Studio product shot |
| `aerial`          | Aerial / drone view |
| `macro`           | Macro close-up |
| `minimalist`      | Minimalist composition |
| `surreal`         | Surrealist / dreamlike |
| `pop_art`         | Pop art style |
| `other`           | Other (model may interpret freely) |

Suggested default in the UI: `photorealistic`.

---

## Generated Images List & Detail

- **List:** `GET /ai/generated-images`  
  Each item can include **`image_style`** (same as in the generate response). Use it to show a “Style” badge or filter by style.

- **Detail:** `GET /ai/generated-images/{image_id}`  
  Returns the full record including **`image_style`**.

No request changes; only the response shape now includes `image_style` where applicable.

---

## Example Frontend Flows

### 1. Dataset images + style from analysis

1. User uploads images via `POST /ai/dataset/analyze` (or fast with URLs).
2. Fetch dataset images: `GET /ai/dataset/{dataset_id}/images`.
3. For each image, read `analysis_result.image_style` and `analysis_result.theme`.
4. Optionally show “Suggested style: cinematic” (e.g. most frequent `image_style` in the dataset) and use that as the default in the generate form.

### 2. Generate with user-chosen style

1. User selects style from dropdown (values from [Image Style Values Reference](#image-style-values-reference)).
2. User enters prompt and optional aspect ratio.
3. Call `POST /ai/generate` with `prompt`, `image_style`, and optionally `folder_id`/`dataset_id`.
4. Display `response.image_url` and `response.image_style` (e.g. “Generated in cinematic style”).

### 3. History with style

1. Call `GET /ai/generated-images`.
2. For each item, show thumbnail, prompt, and `image_style` (e.g. “Style: cinematic”).
3. Optional: filter or sort by `image_style`.

---

## Summary Checklist for Frontend

- [ ] Add **Image Style** dropdown to the generate form using the 20 values from [Image Style Values Reference](#image-style-values-reference).
- [ ] Send **`image_style`** in `POST /ai/generate` when the user selects a style (optional; backend has defaults).
- [ ] Display **`image_style`** in generated image cards and detail view (from generate response and from `GET /ai/generated-images` / `GET /ai/generated-images/{id}`).
- [ ] Optionally use **`theme`** and **`image_style`** from `analysis_result` (dataset images) to show per-image or dataset-level “style” and to suggest a default for generation.

If you want, the next step can be a short “API quick reference” (one-page endpoints + body/response) derived from this doc.

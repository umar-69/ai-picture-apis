# API Documentation

**Base URL:** `https://ai-picture-apis.onrender.com`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Error Responses](#error-responses)
3. [Image Generation (with @-Mention Support)](#image-generation-with--mention-support)
4. [Environments CRUD](#environments-crud)
5. [Folders CRUD](#folders-crud)

---

## Authentication

All Environments and Folders endpoints require a valid JWT. Obtain a token via:

- **POST** `/auth/login` — returns `session.access_token`
- **POST** `/auth/signup` — returns `session.access_token`

Include the token in every request:

```
Authorization: Bearer <access_token>
```

**Example:**

```bash
curl -H "Authorization: Bearer eyJhbGciOiJFUzI1NiIs..." \
  https://ai-picture-apis.onrender.com/environments
```

---

## Error Responses

| Status | Condition | Response Body |
|--------|-----------|---------------|
| 400 | Bad request (validation, etc.) | `{"detail": "..."}` |
| 401 | Invalid or missing token | `{"detail": "Could not validate credentials: ..."}` or `{"detail": "Not authenticated"}` |
| 404 | Resource not found or not owned by user | `{"detail": "Environment not found or not owned by you"}` |
| 500 | Server error | `{"detail": "..."}` |

---

## Image Generation (with @-Mention Support)

Generate images using AI with optional brand style context from environments and folders. When users @-mention an environment or folder in the prompt bar, the backend uses their training data to guide the AI output.

---

### POST /ai/generate

**Description:** Generates an image from a text prompt using the Gemini model. Supports optional brand context via `environment_id` and `folder_id` (used when the user selects an environment/folder from the @-mention dropdown). The backend looks up the referenced folder's training data—`master_prompt` and `dataset_images` analysis (descriptions, tags, colors, vibes)—and injects it into the generation prompt.

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `https://ai-picture-apis.onrender.com/ai/generate` |
| **Auth** | Optional (Bearer token). Anonymous allowed; credits deducted only when authenticated. |
| **Content-Type** | `application/json` |

---

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | The user's image description (e.g. "A professional product photo on white background"). When using @-mentions, the frontend should strip the display text (`@EnvironmentName/FolderName`) before sending—only the IDs matter. |
| `style` | string | No | Style hint (e.g. `"Photorealistic"`). |
| `aspect_ratio` | string | No | Default `"1:1"`. Options: `"1:1"`, `"16:9"`, `"9:16"`, `"4:3"`, `"3:4"`, `"2:3"`, `"3:2"`, `"4:5"`, `"5:4"`, `"21:9"`. |
| `quality` | string | No | Default `"standard"`. |
| `format` | string | No | Default `"png"`. Output format. |
| `dataset_id` | string (UUID) | No | **Legacy / backward compat.** ID of the folder/dataset to use as style reference. Equivalent to `folder_id`. |
| `environment_id` | string (UUID) | No | **NEW.** ID of the environment the user @-mentioned. Use when the user selects an environment (or environment + folder) from the @-mention dropdown. |
| `folder_id` | string (UUID) | No | **NEW.** ID of the folder the user @-mentioned. Maps to `datasets.id`. Use when the user selects a specific folder from the @-mention dropdown. |

**When to send each field:**

| Scenario | What to send |
|----------|--------------|
| User selected `@EnvironmentName/FolderName` | `environment_id`, `folder_id`, and optionally `dataset_id` (same as `folder_id`) |
| User selected only `@EnvironmentName` (no folder) | `environment_id` only |
| User chose a folder via older UI (no @-mention) | `dataset_id` only |
| No reference | Omit all three; prompt is used as-is |

**Note:** `folder_id` and `dataset_id` point to the same thing (`datasets.id`). When both are sent, `folder_id` takes precedence. The backend uses the folder's `master_prompt` + `dataset_images.analysis_result` to build brand context.

---

#### Request Example (with @-mention)

```json
{
  "prompt": "A professional product photo on white background",
  "style": "Photorealistic",
  "aspect_ratio": "1:1",
  "quality": "standard",
  "format": "png",
  "environment_id": "b649f494-3933-4f36-ad81-b99ea3904d68",
  "folder_id": "97dc2876-878d-4271-9bd3-18a978664516"
}
```

**cURL example:**

```bash
curl -X POST "https://ai-picture-apis.onrender.com/ai/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A professional product photo on white background",
    "style": "Photorealistic",
    "environment_id": "b649f494-3933-4f36-ad81-b99ea3904d68",
    "folder_id": "97dc2876-878d-4271-9bd3-18a978664516"
  }'
```

---

#### Response (200)

```json
{
  "id": "aa625db0-f09d-4f1b-8807-1d14d37d7898",
  "image_url": "https://...supabase.co/storage/v1/object/public/generated-images/generated/generated-xxx.png",
  "caption": "A professional product photo on white background",
  "prompt_used": "--- Brand Reference: Product Photos ---\nMaster Style Prompt: ...\n...\nSCENE: A professional product photo on white background",
  "dataset_id": "97dc2876-878d-4271-9bd3-18a978664516",
  "environment_id": "b649f494-3933-4f36-ad81-b99ea3904d68",
  "folder_id": "97dc2876-878d-4271-9bd3-18a978664516",
  "style": "Photorealistic",
  "aspect_ratio": "1:1",
  "quality": "standard",
  "format": "png",
  "resolution": "2K",
  "reference_images_count": 3,
  "credits_used": 5
}
```

---

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Generated image record ID. |
| `image_url` | string | Public URL of the generated image. |
| `caption` | string | Echo of the user's `prompt`. |
| `prompt_used` | string | Full prompt sent to the AI (including injected brand context). Useful for debugging. |
| `dataset_id` | string \| null | The folder ID used for style reference (same as `folder_id` when provided). |
| `environment_id` | string \| null | The environment ID from the request (if any). |
| `folder_id` | string \| null | The folder ID from the request (if any). |
| `style` | string \| null | Style from the request. |
| `aspect_ratio` | string | Aspect ratio used. |
| `quality` | string | Quality setting. |
| `format` | string | Output format. |
| `resolution` | string | Internal resolution (e.g. `"2K"`). |
| `reference_images_count` | integer | Number of reference images used from the folder (0 if none). |
| `credits_used` | integer | Credits deducted (0 if not authenticated). |

---

#### Frontend Integration Flow

1. **@-mention dropdown data**
   - `GET /environments` → list environments (id, name).
   - `GET /environments/{id}/folders` → list folders for each environment (id, name, training_status).

2. **User selects `@EnvironmentName/FolderName`**
   - Strip `@EnvironmentName/FolderName` from the prompt text before sending.
   - In the request body, set:
     - `environment_id` = selected environment's `id`
     - `folder_id` = selected folder's `id`
     - `prompt` = remaining text after stripping the @-mention

3. **User selects `@EnvironmentName` (no folder)**
   - Strip `@EnvironmentName` from the prompt.
   - Set `environment_id` only; omit `folder_id`.
   - Backend uses all trained folders in that environment for broad brand context.

4. **Display response**
   - Use `image_url` for the generated image.
   - Optionally show `prompt_used` or `reference_images_count` in metadata.

---

#### Related Endpoints for @-Mention UX

| Endpoint | Purpose |
|----------|---------|
| `GET /environments` | Populate environment list in @-mention dropdown. |
| `GET /environments/{id}/folders` | Populate folder list for each environment; use `training_status` to show which folders are trained. |
| `GET /ai/dataset/{id}/images` | Fetch images + analysis for a folder (optional; used for thumbnails or preview). |

---

## Environments CRUD

Environments are top-level containers for organizing folders (datasets). Each environment belongs to a user and can contain multiple folders.

---

### 1. List Environments

**Description:** Returns all environments belonging to the authenticated user, ordered by creation date (oldest first).

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `https://ai-picture-apis.onrender.com/environments` |
| **Auth** | Required (Bearer token) |
| **Query params** | None |

**Request example:**

```bash
curl -X GET "https://ai-picture-apis.onrender.com/environments" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200):**

```json
{
  "environments": [
    {
      "id": "a1545528-6701-4b6c-ad83-0289985e0256",
      "user_id": "34f47139-69c6-4c58-9505-fe23d23827fa",
      "name": "Product Shots",
      "created_at": "2026-02-07T21:55:11.01601+00:00"
    }
  ]
}
```

**Response structure:**

| Field | Type | Description |
|-------|------|--------------|
| `environments` | array | List of environment objects |
| `environments[].id` | string (UUID) | Environment ID |
| `environments[].user_id` | string (UUID) | Owner user ID |
| `environments[].name` | string | Environment name |
| `environments[].created_at` | string (ISO 8601) | Creation timestamp |

---

### 2. Create Environment

**Description:** Creates a new environment for the authenticated user.

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `https://ai-picture-apis.onrender.com/environments` |
| **Auth** | Required (Bearer token) |
| **Content-Type** | `application/json` |

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Environment name |

**Request example:**

```bash
curl -X POST "https://ai-picture-apis.onrender.com/environments" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Product Shots"}'
```

**Response (201):**

```json
{
  "id": "a1545528-6701-4b6c-ad83-0289985e0256",
  "user_id": "34f47139-69c6-4c58-9505-fe23d23827fa",
  "name": "Product Shots",
  "created_at": "2026-02-07T21:55:11.01601+00:00"
}
```

**Response structure:**

| Field | Type | Description |
|-------|------|--------------|
| `id` | string (UUID) | Environment ID |
| `user_id` | string (UUID) | Owner user ID |
| `name` | string | Environment name |
| `created_at` | string (ISO 8601) | Creation timestamp |

---

### 3. Update Environment (Rename)

**Description:** Renames an environment. The environment must belong to the authenticated user.

| | |
|---|---|
| **Method** | `PUT` |
| **URL** | `https://ai-picture-apis.onrender.com/environments/{environment_id}` |
| **Auth** | Required (Bearer token) |
| **Content-Type** | `application/json` |

**Path parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `environment_id` | string (UUID) | Yes | ID of the environment to update |

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | New environment name |

**Request example:**

```bash
curl -X PUT "https://ai-picture-apis.onrender.com/environments/a1545528-6701-4b6c-ad83-0289985e0256" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Brand - Environment"}'
```

**Response (200):**

```json
{
  "id": "a1545528-6701-4b6c-ad83-0289985e0256",
  "user_id": "34f47139-69c6-4c58-9505-fe23d23827fa",
  "name": "Brand - Environment",
  "created_at": "2026-02-07T21:55:11.01601+00:00"
}
```

**Error (404):** `{"detail": "Environment not found or not owned by you"}`

---

### 4. Delete Environment

**Description:** Deletes an environment and **all its folders and images** (cascade). The environment must belong to the authenticated user.

| | |
|---|---|
| **Method** | `DELETE` |
| **URL** | `https://ai-picture-apis.onrender.com/environments/{environment_id}` |
| **Auth** | Required (Bearer token) |

**Path parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `environment_id` | string (UUID) | Yes | ID of the environment to delete |

**Request example:**

```bash
curl -X DELETE "https://ai-picture-apis.onrender.com/environments/a1545528-6701-4b6c-ad83-0289985e0256" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200):**

```json
{
  "success": true
}
```

**Error (404):** `{"detail": "Environment not found or not owned by you"}`

---

## Folders CRUD

Folders are datasets inside an environment. Each folder can contain images and has a training status.

---

### 5. List Folders

**Description:** Returns all folders (datasets) within a specific environment. The environment must belong to the authenticated user.

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `https://ai-picture-apis.onrender.com/environments/{environment_id}/folders` |
| **Auth** | Required (Bearer token) |
| **Query params** | None |

**Path parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `environment_id` | string (UUID) | Yes | ID of the parent environment |

**Request example:**

```bash
curl -X GET "https://ai-picture-apis.onrender.com/environments/a1545528-6701-4b6c-ad83-0289985e0256/folders" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200):**

```json
{
  "folders": [
    {
      "id": "02a4db98-d801-4706-bcce-f5bd9b10b1e6",
      "name": "Perfume Bottle Boss",
      "environment_id": "a1545528-6701-4b6c-ad83-0289985e0256",
      "user_id": "34f47139-69c6-4c58-9505-fe23d23827fa",
      "training_status": "not_trained",
      "master_prompt": null,
      "created_at": "2026-02-07T21:55:31.750569+00:00"
    }
  ]
}
```

**Response structure:**

| Field | Type | Description |
|-------|------|--------------|
| `folders` | array | List of folder objects |
| `folders[].id` | string (UUID) | Folder ID |
| `folders[].name` | string | Folder name |
| `folders[].environment_id` | string (UUID) | Parent environment ID |
| `folders[].user_id` | string (UUID) | Owner user ID |
| `folders[].training_status` | string | `"not_trained"` or `"trained"` |
| `folders[].master_prompt` | string \| null | Master prompt for generation (if set) |
| `folders[].created_at` | string (ISO 8601) | Creation timestamp |

**Error (404):** `{"detail": "Environment not found or not owned by you"}`

---

### 6. Create Folder

**Description:** Creates a new folder (dataset) inside an environment. The environment must belong to the authenticated user.

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `https://ai-picture-apis.onrender.com/environments/{environment_id}/folders` |
| **Auth** | Required (Bearer token) |
| **Content-Type** | `application/json` |

**Path parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `environment_id` | string (UUID) | Yes | ID of the parent environment |

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Folder name |

**Request example:**

```bash
curl -X POST "https://ai-picture-apis.onrender.com/environments/a1545528-6701-4b6c-ad83-0289985e0256/folders" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Perfume Bottle Boss"}'
```

**Response (201):**

```json
{
  "id": "02a4db98-d801-4706-bcce-f5bd9b10b1e6",
  "name": "Perfume Bottle Boss",
  "environment_id": "a1545528-6701-4b6c-ad83-0289985e0256",
  "user_id": "34f47139-69c6-4c58-9505-fe23d23827fa",
  "training_status": "not_trained",
  "master_prompt": null,
  "created_at": "2026-02-07T21:55:31.750569+00:00"
}
```

**Error (404):** `{"detail": "Environment not found or not owned by you"}`

---

### 7. Update Folder (Rename)

**Description:** Renames a folder. The folder must belong to the authenticated user.

| | |
|---|---|
| **Method** | `PUT` |
| **URL** | `https://ai-picture-apis.onrender.com/folders/{folder_id}` |
| **Auth** | Required (Bearer token) |
| **Content-Type** | `application/json` |

**Path parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `folder_id` | string (UUID) | Yes | ID of the folder to update |

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | New folder name |

**Request example:**

```bash
curl -X PUT "https://ai-picture-apis.onrender.com/folders/02a4db98-d801-4706-bcce-f5bd9b10b1e6" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Perfume Bottles V2"}'
```

**Response (200):**

```json
{
  "id": "02a4db98-d801-4706-bcce-f5bd9b10b1e6",
  "name": "Perfume Bottles V2",
  "environment_id": "a1545528-6701-4b6c-ad83-0289985e0256",
  "user_id": "34f47139-69c6-4c58-9505-fe23d23827fa",
  "training_status": "not_trained",
  "master_prompt": null,
  "created_at": "2026-02-07T21:55:31.750569+00:00"
}
```

**Error (404):** `{"detail": "Folder not found or not owned by you"}`

---

### 8. Delete Folder

**Description:** Deletes a folder and **all its images** (cascade). Also cleans up image files from Supabase Storage. The folder must belong to the authenticated user.

| | |
|---|---|
| **Method** | `DELETE` |
| **URL** | `https://ai-picture-apis.onrender.com/folders/{folder_id}` |
| **Auth** | Required (Bearer token) |

**Path parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `folder_id` | string (UUID) | Yes | ID of the folder to delete |

**Request example:**

```bash
curl -X DELETE "https://ai-picture-apis.onrender.com/folders/02a4db98-d801-4706-bcce-f5bd9b10b1e6" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200):**

```json
{
  "success": true
}
```

**Error (404):** `{"detail": "Folder not found or not owned by you"}`

---

## Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ai/generate` | Generate image (supports `environment_id`, `folder_id` for @-mention brand context) |
| `GET` | `/environments` | List environments |
| `POST` | `/environments` | Create environment |
| `PUT` | `/environments/{id}` | Rename environment |
| `DELETE` | `/environments/{id}` | Delete environment (cascade) |
| `GET` | `/environments/{id}/folders` | List folders |
| `POST` | `/environments/{id}/folders` | Create folder |
| `PUT` | `/folders/{id}` | Rename folder |
| `DELETE` | `/folders/{id}` | Delete folder (cascade + storage cleanup) |

---

## Data Model

```
Environment (1) ──► (many) Folder/Dataset
                          │
                          └──► (many) Dataset Images
```

- Deleting an **environment** cascades to all its folders and their images.
- Deleting a **folder** cascades to all its images and removes files from Supabase Storage.

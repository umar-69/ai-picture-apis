# AI Picture APIs — Integration Guide for Svelte

Complete API reference for integrating the AI Picture backend with your Svelte frontend.

---

## Base URL

```
https://ai-picture-apis.onrender.com
```

For local development (if running the server locally):

```
http://localhost:8000
```

---

## Authentication

Most endpoints require a Bearer token obtained from `/auth/login`. Include it in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Getting the access token

1. Call `POST /auth/login` with email and password.
2. Extract `session.access_token` from the response.
3. Store it (e.g. in a Svelte store or `localStorage`).
4. Send it with every authenticated request.

### Token lifetime

- Tokens expire after 1 hour (3600 seconds).
- Use `session.refresh_token` and Supabase client to refresh when needed.

---

## Error responses

All errors return JSON:

```json
{
  "detail": "Error message string"
}
```

Common HTTP status codes:

| Code | Meaning                    |
|------|----------------------------|
| 400  | Bad request / validation   |
| 401  | Unauthorized / invalid JWT |
| 402  | Payment required (credits) |
| 403  | Forbidden                  |
| 404  | Not found                  |
| 500  | Server error               |

---

# API Reference

---

## 1. Auth

### POST `/auth/signup`

Create a new user account. Automatically creates profile, credit balance, and Free subscription.

**Auth:** None

**Request body (JSON):**

| Field      | Type   | Required | Description                                            |
|------------|--------|----------|--------------------------------------------------------|
| `email`    | string | Yes      | Valid email address                                    |
| `password` | string | Yes      | User password                                          |
| `metadata` | object | No       | Optional data for profile (see below)                  |

**Metadata (optional):**

| Key            | Type   | Description                                      |
|----------------|--------|--------------------------------------------------|
| `full_name`    | string | Full name (split into first/last if given)       |
| `first_name`   | string | First name                                       |
| `last_name`    | string | Last name                                        |
| `creative_type`| string | e.g. photographer, designer, marketer, artist    |
| `use_case`     | string | What they use the platform for                   |

**Example request:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "metadata": {
    "full_name": "Jane Doe",
    "creative_type": "designer",
    "use_case": "marketing"
  }
}
```

**Example response:**

```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "created_at": "2026-02-07T18:00:00Z",
    "user_metadata": { ... }
  },
  "session": {
    "access_token": "eyJ...",
    "refresh_token": "xyz",
    "expires_in": 3600,
    "expires_at": 1770490889,
    "token_type": "bearer",
    "user": { ... }
  }
}
```

**Svelte fetch example:**

```typescript
const res = await fetch(`${BASE_URL}/auth/signup`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePass123!',
    metadata: { full_name: 'Jane Doe', creative_type: 'designer' }
  })
});
const data = await res.json();
const token = data.session?.access_token;
```

---

### POST `/auth/login`

Log in with email and password.

**Auth:** None

**Request body (JSON):**

| Field      | Type   | Required | Description |
|------------|--------|----------|-------------|
| `email`    | string | Yes      | Email       |
| `password` | string | Yes      | Password    |

**Example response:**

```json
{
  "user": { "id": "uuid", "email": "...", ... },
  "session": {
    "access_token": "eyJ...",
    "refresh_token": "xyz",
    "expires_in": 3600,
    "expires_at": 1770490889,
    "token_type": "bearer",
    "user": { ... }
  }
}
```

**Svelte fetch example:**

```typescript
const res = await fetch(`${BASE_URL}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password })
});
const data = await res.json();
const token = data.session?.access_token;
```

---

### POST `/auth/logout`

Log out. No token required; client should discard the stored token.

**Auth:** None

**Example response:**

```json
{
  "message": "Logged out successfully"
}
```

---

## 2. Users

### GET `/users/me`

Get the current authenticated user.

**Auth:** Required (Bearer token)

**Example response:**

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "created_at": "2026-02-07 18:00:00",
  "last_sign_in_at": "2026-02-07 18:26:44",
  "app_metadata": { "provider": "email", "providers": ["email"] },
  "user_metadata": { "full_name": "Jane Doe", ... }
}
```

**Svelte fetch example:**

```typescript
const res = await fetch(`${BASE_URL}/users/me`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
const user = await res.json();
```

---

### DELETE `/users/me`

Permanently delete the current user account.

**Auth:** Required (Bearer token)

**Example response:**

```json
{
  "message": "Account deleted successfully"
}
```

---

## 3. Account (Profile, Credits, Subscription)

### GET `/account/profile`

Get the current user's profile (first name, last name, creative type, use case, avatar).

**Auth:** Required

**Example response:**

```json
{
  "id": "uuid",
  "first_name": "Jane",
  "last_name": "Designer",
  "creative_type": "photographer",
  "use_case": "social media content",
  "avatar_url": null,
  "updated_at": "2026-02-07T18:26:34Z",
  "created_at": "2026-02-07T18:26:34Z"
}
```

---

### PUT `/account/profile`

Create or update the user profile. Send only fields you want to change.

**Auth:** Required

**Request body (JSON):**

| Field          | Type   | Required | Description                                 |
|----------------|--------|----------|---------------------------------------------|
| `first_name`   | string | No       | First name                                  |
| `last_name`    | string | No       | Last name                                   |
| `creative_type`| string | No       | e.g. photographer, designer, marketer      |
| `use_case`     | string | No       | What they use the platform for             |
| `avatar_url`   | string | No       | URL to avatar image                        |

**Example request:**

```json
{
  "first_name": "Jane",
  "last_name": "Designer",
  "creative_type": "photographer",
  "use_case": "social media content"
}
```

---

### GET `/account/subscription`

Get the current subscription and plan details.

**Auth:** Required

**Example response:**

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "plan_id": "uuid",
  "status": "active",
  "stripe_subscription_id": null,
  "current_period_start": "2026-02-07T18:26:34Z",
  "current_period_end": "2026-03-09T18:26:34Z",
  "created_at": "2026-02-07T18:26:34Z",
  "plan": {
    "id": "uuid",
    "name": "Free",
    "credit_limit": 50,
    "price_monthly": 0.0,
    "features": ["50 credits/month", "Basic image generation", ...],
    "created_at": "..."
  }
}
```

---

### GET `/account/credits`

Get the current credit balance.

**Auth:** Required

**Example response:**

```json
{
  "user_id": "uuid",
  "total_credits": 50,
  "used_credits": 0,
  "remaining_credits": 50,
  "last_reset_at": "2026-02-07T18:26:34Z",
  "updated_at": "2026-02-07T18:26:34Z"
}
```

---

### GET `/account/credits/history`

Get paginated credit transaction history (adds, deductions, etc.).

**Auth:** Required

**Query params:**

| Param   | Type | Default | Description              |
|---------|------|---------|--------------------------|
| `limit` | int  | 20      | 1–100                    |
| `offset`| int  | 0       | Pagination offset        |

**Example:** `GET /account/credits/history?limit=10&offset=0`

**Example response:**

```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "amount": -5,
    "type": "generation",
    "description": "generate_image: -5 credits",
    "metadata": { "generation_id": "uuid", "resolution": "2K" },
    "created_at": "2026-02-07T18:30:00Z"
  },
  {
    "id": "uuid",
    "user_id": "uuid",
    "amount": 50,
    "type": "subscription_reset",
    "description": "Initial 50 credits from Free plan",
    "metadata": {},
    "created_at": "2026-02-07T18:26:34Z"
  }
]
```

---

### GET `/account/usage`

Get paginated usage logs (each action and its credit cost).

**Auth:** Required

**Query params:**

| Param   | Type | Default | Description       |
|---------|------|---------|-------------------|
| `limit` | int  | 20      | 1–100             |
| `offset`| int  | 0       | Pagination offset |

**Example response:**

```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "action_type": "generate_image",
    "prompt": "A modern living room",
    "credits_used": 5,
    "metadata": { "generation_id": "uuid" },
    "created_at": "2026-02-07T18:30:00Z"
  }
]
```

---

### GET `/account/summary`

Combined dashboard data: profile, subscription, credits, recent usage.

**Auth:** Required

**Example response:**

```json
{
  "profile": { "id": "...", "first_name": "Jane", ... },
  "subscription": { "status": "active", "plan": { "name": "Free", ... }, ... },
  "credits": { "total_credits": 50, "used_credits": 0, "remaining_credits": 50, ... },
  "recent_usage": [
    { "action_type": "generate_image", "credits_used": 5, "prompt": "...", ... }
  ]
}
```

---

### GET `/account/plans`

List all available plans (Free, Pro, Enterprise). No auth required.

**Auth:** None

**Example response:**

```json
[
  {
    "id": "uuid",
    "name": "Free",
    "credit_limit": 50,
    "price_monthly": 0.0,
    "features": ["50 credits/month", "Basic image generation", ...],
    "created_at": "..."
  },
  {
    "id": "uuid",
    "name": "Pro",
    "credit_limit": 500,
    "price_monthly": 19.99,
    "features": ["500 credits/month", "HD image generation", ...],
    "created_at": "..."
  },
  {
    "id": "uuid",
    "name": "Enterprise",
    "credit_limit": 2000,
    "price_monthly": 49.99,
    "features": ["2000 credits/month", ...],
    "created_at": "..."
  }
]
```

---

## 4. Business Profile

### GET `/business/`

Get the current user's business profile (brand, theme, vibes, etc.).

**Auth:** Required

**Example response:**

```json
{
  "id": "uuid",
  "business_name": "My Brand",
  "theme": "modern",
  "target_audience": "young professionals",
  "vibes": "minimal, clean",
  "logo_url": "https://...",
  "created_at": "2026-02-07T18:00:00Z"
}
```

---

### POST `/business/`

Create or update the business profile.

**Auth:** Required

**Request body (JSON):**

| Field            | Type   | Required | Description               |
|------------------|--------|----------|---------------------------|
| `business_name`  | string | Yes      | Business name             |
| `theme`          | string | No       | Brand theme               |
| `target_audience`| string | No       | Target audience           |
| `vibes`          | string | No       | Style/vibes               |
| `logo_url`       | string | No       | Logo URL                  |

---

## 5. Storage

### POST `/storage/upload`

Upload a single file to Supabase Storage.

**Auth:** Optional (works for anonymous users)

**Request:** `multipart/form-data`

| Field        | Type   | Required | Description                    |
|--------------|--------|----------|--------------------------------|
| `file`       | file   | Yes      | File to upload                 |
| `dataset_id` | string | No       | Folder/dataset ID (or `temp`)  |

**Example response:**

```json
{
  "file_path": "dataset-uuid/abc123.jpg",
  "public_url": "https://...supabase.co/storage/v1/object/public/dataset-images/..."
}
```

**Svelte fetch example:**

```typescript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('dataset_id', datasetId);

const res = await fetch(`${BASE_URL}/storage/upload`, {
  method: 'POST',
  headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  body: formData
});
const { file_path, public_url } = await res.json();
```

---

### POST `/storage/upload-multiple`

Upload multiple files.

**Auth:** Optional

**Request:** `multipart/form-data`

| Field        | Type   | Required | Description                 |
|--------------|--------|----------|-----------------------------|
| `files`      | files  | Yes      | One or more files           |
| `dataset_id` | string | No       | Folder/dataset ID           |

**Example response:**

```json
{
  "files": [
    { "file_path": "...", "public_url": "https://...", "filename": "img1.jpg" },
    { "file_path": "...", "public_url": "https://...", "filename": "img2.jpg" }
  ],
  "count": 2
}
```

---

### GET `/storage/list`

List files in the current user's storage folder.

**Auth:** Required

**Example response:** Array of storage objects (paths, metadata).

---

## 6. AI — Image Generation

### POST `/ai/generate`

Generate an image with Gemini (2K resolution). Uses business profile and dataset context when available.

**Auth:** Optional (anonymous allowed; credits deducted only when logged in)

**Request body (JSON):**

| Field         | Type   | Required | Default   | Description                                      |
|---------------|--------|----------|-----------|--------------------------------------------------|
| `prompt`      | string | Yes      | —         | Image description                                |
| `style`       | string | No       | —         | Style hint                                       |
| `aspect_ratio`| string | No       | `"1:1"`   | 1:1, 16:9, 9:16, 4:3, 3:4, 2:3, 3:2, 4:5, 5:4, 21:9 |
| `quality`     | string | No       | `"standard"` | Quality hint                                 |
| `format`      | string | No       | `"png"`   | png, jpg, etc.                                  |
| `dataset_id`  | string | No       | —         | Dataset for style reference (up to 5 images)    |

**Credits:** 5 credits per generation (for logged-in users).

**Example request:**

```json
{
  "prompt": "A modern living room with natural light",
  "style": "minimalist Scandinavian",
  "aspect_ratio": "16:9",
  "dataset_id": "uuid-of-dataset"
}
```

**Example response:**

```json
{
  "id": "uuid",
  "image_url": "https://.../generated/generated-xxx.png",
  "caption": "A modern living room with natural light",
  "prompt_used": "Full prompt used by model...",
  "dataset_id": "uuid",
  "style": "minimalist Scandinavian",
  "aspect_ratio": "16:9",
  "quality": "standard",
  "format": "png",
  "resolution": "2K",
  "reference_images_count": 3,
  "credits_used": 5
}
```

**402 response (insufficient credits):**

```json
{
  "detail": "Insufficient credits. Need 5, have 3. Upgrade your plan for more credits."
}
```

---

### GET `/ai/generated-images`

List generated images for the current user.

**Auth:** Optional (user-filtered when logged in)

**Query params:**

| Param        | Type   | Default | Description              |
|--------------|--------|---------|--------------------------|
| `limit`      | int    | 50      | Number of images         |
| `offset`     | int    | 0       | Pagination offset        |
| `dataset_id` | string | —       | Filter by dataset        |

**Example response:**

```json
{
  "images": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "prompt": "A modern living room",
      "full_prompt": "...",
      "image_url": "https://...",
      "dataset_id": "uuid",
      "style": "...",
      "aspect_ratio": "16:9",
      "quality": "standard",
      "format": "png",
      "resolution": "2K",
      "reference_images_count": 3,
      "unique_visual_elements": [...],
      "created_at": "2026-02-07T18:30:00Z"
    }
  ],
  "count": 1,
  "offset": 0,
  "limit": 50
}
```

---

### GET `/ai/generated-images/{image_id}`

Get a single generated image by ID.

**Auth:** Optional (ownership check when logged in)

---

## 7. AI — Dataset Analysis

### POST `/ai/dataset/analyze`

Upload images, analyze them with Gemini, and store results in a dataset. Creates the dataset if it does not exist.

**Auth:** Optional (credits deducted only when logged in)

**Request:** `multipart/form-data`

| Field         | Type   | Required | Description                 |
|---------------|--------|----------|-----------------------------|
| `dataset_id`  | string | Yes      | Dataset ID (or `datasetId`) |
| `datasetId`   | string | Yes*     | Alias for `dataset_id`     |
| `files`       | files  | Yes      | One or more image files     |

*Use either `dataset_id` or `datasetId`.

**Credits:** 1 credit per successfully analyzed image.

**Example response:**

```json
{
  "results": [
    {
      "id": "uuid",
      "dataset_id": "uuid",
      "image_url": "https://...",
      "analysis_result": {
        "description": "...",
        "tags": ["Marble", "Natural light", ...],
        "lighting": "Natural, soft",
        "colors": "White, beige, wood",
        "vibe": "Calm, minimalist"
      },
      "created_at": "..."
    }
  ],
  "credits_used": 3
}
```

---

### POST `/ai/dataset/analyze-fast`

Analyze images by URL (useful when images are already hosted). Processes multiple images in parallel.

**Auth:** Optional (credits deducted only when logged in)

**Request body (JSON):**

| Field        | Type     | Required | Description                |
|--------------|----------|----------|----------------------------|
| `dataset_id` | string   | Yes      | Dataset ID                 |
| `image_urls` | string[] | Yes      | Public URLs of images      |

**Credits:** 1 credit per successfully analyzed image.

**Example request:**

```json
{
  "dataset_id": "uuid",
  "image_urls": [
    "https://example.com/image1.jpg",
    "https://example.com/image2.jpg"
  ]
}
```

**Example response:**

```json
{
  "results": [
    {
      "id": "uuid",
      "dataset_id": "uuid",
      "image_url": "https://...",
      "analysis_result": { "tags": [...], "description": "...", ... }
    }
  ],
  "total_processed": 2,
  "successful": 2,
  "credits_used": 2
}
```

---

### GET `/ai/dataset/{dataset_id}/images`

Get all images and their analysis results for a dataset.

**Auth:** Optional

**Example response:**

```json
{
  "images": [
    {
      "id": "uuid",
      "dataset_id": "uuid",
      "image_url": "https://...",
      "analysis_result": {
        "description": "...",
        "tags": [...],
        "lighting": "...",
        "colors": "...",
        "vibe": "..."
      },
      "created_at": "..."
    }
  ]
}
```

---

### PATCH `/ai/dataset/{dataset_id}/training-status`

Update the training status of a dataset.

**Auth:** Optional (ownership checked when logged in)

**Request:** `application/x-www-form-urlencoded` or `multipart/form-data`

| Field            | Type   | Required | Description                      |
|------------------|--------|----------|----------------------------------|
| `training_status`| string | Yes      | `"trained"` or `"not_trained"`   |

**Example:** `training_status=trained`

**Example response:**

```json
{
  "success": true,
  "dataset_id": "uuid",
  "training_status": "trained",
  "message": "Dataset training status updated to 'trained'"
}
```

---

## Credit Costs Summary

| Action                | Credits |
|-----------------------|---------|
| Generate image        | 5       |
| Analyze image (upload)| 1       |
| Analyze image (URL)   | 1       |

---

## Svelte Integration Tips

### 1. API client store

```typescript
// lib/api.ts
const BASE_URL = 'https://ai-picture-apis.onrender.com';

export function getAuthHeaders() {
  const token = typeof window !== 'undefined' && localStorage.getItem('token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export async function api(path: string, options: RequestInit = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options.headers
    }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}
```

### 2. Form data (uploads)

For `multipart/form-data`, do not set `Content-Type`; the browser will set it with the boundary.

```typescript
const formData = new FormData();
formData.append('file', file);
formData.append('dataset_id', datasetId);

const res = await fetch(`${BASE_URL}/storage/upload`, {
  method: 'POST',
  headers: getAuthHeaders(),
  body: formData
});
```

### 3. Handle 402 (insufficient credits)

```typescript
if (res.status === 402) {
  const { detail } = await res.json();
  // Redirect to upgrade / show upgrade modal
  showUpgradeModal(detail);
}
```

### 4. Typical flow

1. **Signup/Login** → store `session.access_token`
2. **Dashboard** → `GET /account/summary`
3. **Profile** → `GET /account/profile`, `PUT /account/profile`
4. **Credits** → `GET /account/credits` before expensive actions
5. **Generate** → `POST /ai/generate` with token for credit deduction
6. **Analyze** → `POST /ai/dataset/analyze` or `analyze-fast`

---

## OpenAPI / Swagger

Interactive docs are available at:

```
https://ai-picture-apis.onrender.com/docs
```

ReDoc:

```
https://ai-picture-apis.onrender.com/redoc
```

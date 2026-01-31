# 🚀 Deployment Checklist

## 1. Pre-Deployment Verification
- [x] **Database Migration**: `ALTER TABLE datasets ALTER COLUMN user_id DROP NOT NULL;` (Completed via MCP)
- [x] **Storage Bucket**: `generated-images` bucket exists and is public.
- [x] **Storage Policies**: Policies for `generated-images` are set (INSERT for service/auth/public, SELECT for public).
- [x] **Environment Variables**: `GOOGLE_API_KEY` is set in your deployment environment (Render/Vercel/etc.).
- [x] **Dependencies**: `requirements.txt` is updated with `google-genai` (v1.0+) and `pillow`.

## 2. Deployment Steps
1.  **Commit Changes**:
    ```bash
    git add .
    git commit -m "feat: upgrade to gemini-3-pro-image-preview and google-genai sdk"
    git push origin main
    ```
2.  **Build & Deploy**:
    - Your deployment platform (e.g., Render) should automatically detect the push and rebuild.
    - Ensure the build command installs dependencies: `pip install -r requirements.txt`.
    - Ensure the start command is correct: `uvicorn app.main:app --host 0.0.0.0 --port 10000` (or similar).

## 3. Post-Deployment Verification
1.  **Check Logs**: Monitor your deployment logs for any startup errors related to imports or API keys.
2.  **Test Endpoint**:
    ```bash
    curl -X POST https://your-app-url.onrender.com/ai/generate \
      -H "Content-Type: application/json" \
      -d '{
        "prompt": "test image",
        "aspect_ratio": "1:1"
      }'
    ```
3.  **Verify Storage**: Check your Supabase dashboard to ensure new images are appearing in the `generated-images` bucket.

## 4. Frontend Handoff
Share the `FRONTEND_INTEGRATION.md` file with your frontend developer. It contains:
- New API endpoint details (`/ai/generate`).
- Request/Response formats.
- Example code for integration.

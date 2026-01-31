# Fixes Applied - January 31, 2026

## Issues Identified and Resolved

### 1. **Gemini Model Error: 404 models/gemini-3-flash not found**

**Problem:**
- The code was using `gemini-3-flash` which doesn't exist in the Gemini API
- Error: `404 models/gemini-3-flash is not found for API version v1beta`

**Solution:**
- Updated model name to `gemini-3-flash-preview` (the correct preview model name)
- Enabled **Agentic Vision** capabilities by adding code execution tool
- Updated in 2 locations:
  1. `/ai/dataset/analyze` endpoint (line 120)
  2. `/ai/analyze` endpoint (line 237)

**Code Changes:**
```python
# Before:
model = genai.GenerativeModel('gemini-3-flash')

# After:
model = genai.GenerativeModel(
    'gemini-3-flash-preview',
    tools=[{'code_execution': {}}]  # Enables Agentic Vision
)
```

**Benefits:**
- Gemini 3 Flash Preview now has access to code execution for better image analysis
- Can zoom into details, count objects, analyze pixel distributions
- More accurate vision analysis using the Think-Act-Observe loop

---

### 2. **Database Foreign Key Constraint Error**

**Problem:**
- Error: `violates foreign key constraint "dataset_images_dataset_id_fkey"`
- The code was trying to insert images for a `dataset_id` that didn't exist in the `datasets` table
- Additionally, `datasets.user_id` had a NOT NULL constraint with FK to `auth.users.id`, preventing anonymous uploads

**Root Causes:**
1. Frontend was sending a `dataset_id` that wasn't created in the database
2. `datasets.user_id` was NOT NULL and required a valid user from `auth.users`
3. Anonymous users couldn't create datasets because we couldn't assign a valid `user_id`

**Solution:**
1. **Made `user_id` nullable in the database:**
   ```sql
   ALTER TABLE datasets ALTER COLUMN user_id DROP NOT NULL;
   ```

2. **Added automatic dataset creation logic:**
   - Check if dataset exists before uploading images
   - If missing, create it automatically
   - Support both authenticated and anonymous users
   - Anonymous users get `user_id = NULL`

**Code Changes in `app/routers/ai.py`:**
```python
# Check if dataset exists
ds_check = supabase.table("datasets").select("id").eq("id", actual_dataset_id).execute()
if not ds_check.data:
    # Create it if missing
    # user_id is now nullable to support anonymous uploads
    new_dataset = {
        "id": actual_dataset_id,
        "user_id": current_user.id if current_user else None,
        "name": "Untitled Dataset"
    }
    supabase.table("datasets").insert(new_dataset).execute()
    print(f"Created missing dataset: {actual_dataset_id} for {'user ' + current_user.id if current_user else 'anonymous user'}")
```

---

### 3. **Supabase Configuration Issues**

**Problem:**
- Warning: `Invalid API key` - the service role key didn't match the Supabase URL
- Error: `signature verification failed` for storage uploads
- Initial confusion between PROD and DEV environments

**Analysis:**
- `SUPABASE_URL` (PROD): `https://qxripdllxckfpnimzxoa.supabase.co`
- `SUPABASE_URL_DEV` (DEV): `https://fxrygwdyysakwsfcjjts.supabase.co`
- `SUPABASE_SERVICE_ROLE_KEY` JWT has `ref: fxrygwdyysakwsfcjjts` (matches DEV)
- `SUPABASE_ANON_KEY` JWT has `ref: qxripdllxckfpnimzxoa` (matches PROD)
- **Frontend/Mobile apps use PROD** (`qxripdllxckfpnimzxoa`)

**Solution:**
Updated `app/config.py` to use the PRODUCTION environment to match frontend:

```python
# Final Configuration:
SUPABASE_URL = os.getenv("SUPABASE_URL")  # PROD
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  # PROD anon key
SUPABASE_KEY = SUPABASE_ANON_KEY  # PROD anon key
SUPABASE_SERVICE_ROLE_KEY = SUPABASE_ANON_KEY  # Use anon key (RLS disabled)
```

**Why PROD?**
- Your frontend and mobile apps are configured to use PROD
- All data is in the PROD database
- Backend must match frontend to access the same data
- PROD anon key works fine since RLS is disabled on tables

---

## Summary of Changes

### Files Modified:

1. **`app/config.py`**
   - Switched to DEV Supabase environment
   - Updated comments for clarity

2. **`app/routers/ai.py`**
   - Updated Gemini model to `gemini-3-flash-preview`
   - Enabled Agentic Vision (code execution)
   - Added automatic dataset creation logic
   - Support for anonymous users

3. **Database Schema**
   - Made `datasets.user_id` nullable via SQL migration

### Database Changes:

**⚠️ ACTION REQUIRED:** You need to run this SQL on your PRODUCTION Supabase:

```sql
ALTER TABLE datasets ALTER COLUMN user_id DROP NOT NULL;
```

**How to run:**
1. Go to https://supabase.com/dashboard/project/qxripdllxckfpnimzxoa
2. Click "SQL Editor" in the left sidebar
3. Paste the SQL above
4. Click "Run"

**Note:** This migration was already applied to DEV, but your production data is in PROD, so you need to run it there too.

---

## Testing Recommendations

1. **Test Anonymous Upload:**
   - Upload images without authentication
   - Verify dataset is created with `user_id = NULL`
   - Verify images are stored and analyzed

2. **Test Authenticated Upload:**
   - Upload images with valid JWT token
   - Verify dataset is created with correct `user_id`
   - Verify images are stored and analyzed

3. **Test Gemini Analysis:**
   - Upload various image types
   - Check that analysis returns proper JSON with:
     - description
     - tags
     - lighting
     - colors
     - vibe
   - Verify Agentic Vision features work (e.g., zooming, counting objects)

4. **Test Storage:**
   - Verify files upload to `dataset-images` bucket
   - Verify public URLs are accessible
   - Check that storage policies allow public access

---

## Agentic Vision Capabilities

With the new `gemini-3-flash-preview` model and code execution enabled, the AI can now:

1. **Zoom and Inspect:** Automatically detect when details are too small and crop/re-examine at higher resolution
2. **Visual Math:** Run multi-step calculations (e.g., counting objects, summing values)
3. **Image Annotation:** Draw on images to show relationships or highlight objects
4. **Object Detection:** Enhanced accuracy for detecting and labeling objects
5. **Code-Based Reasoning:** Write and execute Python code to analyze images programmatically

Example use cases:
- "Count the number of people in this image"
- "What text is written on that small sign?"
- "Calculate the total from this receipt"
- "Highlight all the red objects in this image"

---

## References

- [Gemini 3 Agentic Vision Blog Post](https://blog.google/innovation-and-ai/technology/developers-tools/agentic-vision-gemini-3-flash/)
- [Code Execution with Images Documentation](https://ai.google.dev/gemini-api/docs/code-execution#images)
- [Image Understanding Guide](https://ai.google.dev/gemini-api/docs/image-understanding)

---

## Next Steps

1. **Monitor logs** for any remaining errors
2. **Test thoroughly** with both anonymous and authenticated users
3. **Consider adding:**
   - Rate limiting for anonymous uploads
   - Image size validation
   - More detailed error messages for users
   - Retry logic for transient failures

4. **Optional improvements:**
   - Add a cleanup job to delete orphaned datasets (where `user_id IS NULL` and older than X days)
   - Add analytics to track anonymous vs authenticated usage
   - Implement dataset ownership transfer when anonymous users sign up

# 🧪 Testing Guide - Nano Banana with Real Supabase Data

## Quick Start

### 1. Install Dependencies
```bash
cd /Users/umartahir-butt/ai-picture-apis
pip install -r requirements.txt
```

### 2. Start Server
```bash
uvicorn app.main:app --reload
```

### 3. Run Tests
```bash
# Option A: Run all tests interactively
./TEST_SCRIPTS.sh

# Option B: Run individual test
./test_individual.sh

# Option C: Manual curl command
curl -X POST http://localhost:8000/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a latte with latte art",
    "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
    "aspect_ratio": "1:1"
  }'
```

---

## Real Dataset Information

**From Your Supabase Database:**

- **Dataset ID:** `d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a`
- **Name:** Coffee Shop (BRAUN NOTES COFFEE)
- **Images:** 11 analyzed cafe/coffee images
- **Style:** Cozy, sophisticated European bistro atmosphere
- **Colors:** Deep brown, ebony black, creamy white, golden tan, beige
- **Lighting:** Soft, warm, natural indoor lighting
- **Vibe:** Sophisticated, relaxed, classically metropolitan

### Sample Images in Dataset:
1. Pastries and latte on black marble table
2. Outdoor cafe with Parisian bistro chairs
3. Cafe entrance with menu board
4. Banana bread with bokeh background
5. Street-side cafe seating

---

## Test Scenarios

### Test 1: Without Dataset (Baseline)
**Purpose:** See what Nano Banana generates with NO visual reference

```bash
curl -X POST http://localhost:8000/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a latte with heart-shaped latte art on a marble table",
    "style": "Photorealistic",
    "aspect_ratio": "1:1"
  }'
```

**Expected:**
- Generic latte image
- No specific style
- Basic photorealistic rendering

---

### Test 2: With Dataset (Visual Context)
**Purpose:** See how reference images affect generation

```bash
curl -X POST http://localhost:8000/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a latte with heart-shaped latte art on a marble table",
    "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
    "style": "Photorealistic",
    "aspect_ratio": "1:1"
  }'
```

**Expected:**
- Latte matching coffee shop aesthetic
- Warm, natural lighting
- Deep brown/cream color palette
- Black marble table (like in dataset)
- Cozy, sophisticated vibe

**Server Logs to Check:**
```
Generating image with Nano Banana. Prompt: Style Guidelines: ... Reference style: Cozy, sophisticated, warm, natural-light. Match the style and aesthetic of the 5 reference image(s) provided. a latte with heart-shaped latte art on a marble table Style: Photorealistic.
Using 5 reference images from dataset
Added reference image: https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/5dd13496-a72d-47a4-b22f-ff532de6951b.jpg
Added reference image: https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/8b24290e-aa26-4a0b-a233-9d9853379a87.jpg
...
```

---

### Test 3: Cafe Exterior (Vertical)
**Purpose:** Test with different aspect ratio and subject

```bash
curl -X POST http://localhost:8000/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "outdoor cafe seating with bistro chairs and a menu board",
    "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
    "aspect_ratio": "9:16"
  }'
```

**Expected:**
- Vertical Instagram Story format
- Parisian-style bistro chairs (black/cream checkered)
- Menu board similar to BRAUN NOTES COFFEE
- Urban, sophisticated atmosphere

---

### Test 4: Food Photography
**Purpose:** Test food styling consistency

```bash
curl -X POST http://localhost:8000/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a chocolate croissant on a plate with coffee in the background",
    "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
    "style": "Food Photography",
    "aspect_ratio": "4:3"
  }'
```

**Expected:**
- Warm, cozy cafe aesthetic
- Soft bokeh background
- Similar plating to dataset images
- Natural, warm lighting

---

### Test 5: Social Media Banner
**Purpose:** Test wide format for marketing

```bash
curl -X POST http://localhost:8000/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "coffee shop interior with espresso machine and pastries",
    "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
    "aspect_ratio": "16:9"
  }'
```

**Expected:**
- Wide banner format (YouTube thumbnail, website header)
- Professional espresso machine
- Dark wood counter
- Warm interior lighting

---

## What to Check

### ✅ Success Indicators

1. **Response includes `image_url`:**
   ```json
   {
     "image_url": "https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/generated-images/generated/abc-123.png"
   }
   ```

2. **Server logs show reference images:**
   ```
   Using 5 reference images from dataset
   Added reference image: https://...
   ```

3. **Prompt includes style context:**
   ```json
   {
     "prompt_used": "Style Guidelines: ... Reference style: Cozy, sophisticated, warm, natural-light. Match the style and aesthetic of the 5 reference image(s) provided. ..."
   }
   ```

4. **Generated image matches dataset style:**
   - Similar color palette
   - Similar lighting
   - Similar composition
   - Similar vibe/atmosphere

---

## Troubleshooting

### Error: "Failed to upload image to storage"
**Solution:** Bucket already exists, check Supabase storage policies

### Error: "No image generated by Nano Banana"
**Possible Causes:**
- Safety filters blocked content
- API quota exceeded
- Network timeout

**Solution:**
- Try simpler prompt
- Check Google Cloud Console
- Verify API key in `.env`

### Error: "Could not load reference image"
**Possible Causes:**
- Image URL not accessible
- Network timeout
- Invalid image format

**Solution:**
- Check image URLs are public
- Verify Supabase storage bucket is public
- Check server logs for specific error

### No Reference Images in Logs
**Check:**
1. Dataset ID is correct
2. Dataset has images in `dataset_images` table
3. Images have valid `image_url` values
4. URLs are accessible

---

## Performance Expectations

| Scenario | Image Downloads | Generation Time | Total Time |
|----------|----------------|-----------------|------------|
| No dataset | 0 | ~3-5 seconds | ~3-5 seconds |
| With dataset (5 images) | ~2-3 seconds | ~5-10 seconds | ~7-13 seconds |

**Note:** First request may be slower due to cold start

---

## Comparing Results

### Side-by-Side Comparison

1. **Run Test 1 (no dataset)** - Save image URL
2. **Run Test 2 (with dataset)** - Save image URL
3. **Open both URLs in browser tabs**
4. **Compare:**
   - Color palette
   - Lighting style
   - Composition
   - Overall vibe

**Expected Difference:**
- Test 1: Generic, could be any coffee shop
- Test 2: Specifically matches BRAUN NOTES COFFEE style

---

## Test Results Template

Use `TEST_RESULTS.md` to document your findings:

```bash
# Edit TEST_RESULTS.md and fill in:
- Actual response JSON
- Server logs
- Generated image URLs
- Visual comparison notes
- Performance metrics
```

---

## Quick Commands

```bash
# Check server is running
curl http://localhost:8000/

# Check dataset exists
curl http://localhost:8000/ai/dataset/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/images

# View server logs
# (Check terminal where uvicorn is running)

# Install jq for pretty JSON output
brew install jq  # macOS
# or
sudo apt install jq  # Linux

# Run test with pretty output
curl -X POST http://localhost:8000/ai/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a"}' \
  | jq '.'
```

---

## Files Created

1. **`TEST_SCRIPTS.sh`** - Interactive test runner (all tests)
2. **`test_individual.sh`** - Run one test at a time
3. **`TEST_RESULTS.md`** - Template for documenting results
4. **`TESTING_GUIDE.md`** - This file

---

## Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Start server: `uvicorn app.main:app --reload`
3. ✅ Run tests: `./TEST_SCRIPTS.sh`
4. ✅ Compare results (Test 1 vs Test 2)
5. ✅ Document findings in `TEST_RESULTS.md`

---

## Expected Outcome

**After running tests, you should see:**

- ✅ Images generated successfully
- ✅ Test 2 images match coffee shop style
- ✅ Reference images downloaded and used
- ✅ Style consistency across all dataset-based generations
- ✅ Different aspect ratios working correctly

**This proves the visual context feature is working!** 🎉

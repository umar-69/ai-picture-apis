# Test Results Template

## Dataset Information

**Dataset ID:** `d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a`  
**Dataset Name:** Coffee Shop (BRAUN NOTES COFFEE)  
**Image Count:** 11 images  
**Style:** Cozy, sophisticated European bistro atmosphere  

### Dataset Images (First 5 used as reference):

1. **Image 1:** Pastries and latte on marble table
   - URL: `https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/5dd13496-a72d-47a4-b22f-ff532de6951b.jpg`
   - Vibe: Cozy, sophisticated, inviting
   - Colors: Deep brown, ebony black, creamy white, golden tan
   - Lighting: Soft, warm, natural indoor lighting

2. **Image 2:** Outdoor cafe with menu board
   - URL: `https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/8b24290e-aa26-4a0b-a233-9d9853379a87.jpg`
   - Vibe: Sophisticated, relaxed, classically metropolitan
   - Style: Parisian-style bistro chairs

3. **Image 3:** Cafe entrance with bistro chairs
   - URL: `https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/289c4643-a4dc-41c9-aa61-c530cc8ae54d.jpg`
   - Vibe: Cozy, sophisticated, invitingly urban

4. **Image 4:** Banana bread slice
   - URL: `https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/35582783-14bc-43c1-8b9e-51014de65dae.jpeg`
   - Vibe: Cozy, inviting, sophisticated urban cafe
   - Lighting: Warm, ambient interior with soft bokeh

5. **Image 5:** Outdoor cafe seating
   - URL: `https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/b41a931d-b0ab-4bdf-8d7b-cec89f568f5d.jpeg`
   - Vibe: Relaxed, sophisticated, inviting urban atmosphere

---

## Test 1: WITHOUT Dataset (Text-Only)

### Request:
```json
{
  "prompt": "a latte with heart-shaped latte art on a marble table",
  "style": "Photorealistic",
  "aspect_ratio": "1:1"
}
```

### Expected Result:
- Generic latte image
- No specific style matching
- Basic photorealistic rendering

### Actual Response:
```json
{
  "image_url": "PASTE_URL_HERE",
  "caption": "a latte with heart-shaped latte art on a marble table",
  "prompt_used": "a latte with heart-shaped latte art on a marble table Style: Photorealistic.",
  "style": "Photorealistic",
  "aspect_ratio": "1:1"
}
```

### Server Logs:
```
PASTE_LOGS_HERE
```

---

## Test 2: WITH Dataset (Visual Context)

### Request:
```json
{
  "prompt": "a latte with heart-shaped latte art on a marble table",
  "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
  "style": "Photorealistic",
  "aspect_ratio": "1:1"
}
```

### Expected Result:
- Latte matching coffee shop style
- Cozy, sophisticated European cafe aesthetic
- Warm, natural lighting
- Deep brown, cream, black color palette
- Similar marble table texture

### Actual Response:
```json
{
  "image_url": "PASTE_URL_HERE",
  "caption": "a latte with heart-shaped latte art on a marble table",
  "prompt_used": "Style Guidelines: ... Reference style: Cozy, sophisticated, warm, natural-light. Match the style and aesthetic of the 5 reference image(s) provided. a latte with heart-shaped latte art on a marble table Style: Photorealistic.",
  "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
  "style": "Photorealistic",
  "aspect_ratio": "1:1"
}
```

### Server Logs:
```
Generating image with Nano Banana. Prompt: Style Guidelines: ... Reference style: Cozy, sophisticated, warm, natural-light. Match the style and aesthetic of the 5 reference image(s) provided. a latte with heart-shaped latte art on a marble table Style: Photorealistic.
Using 5 reference images from dataset
Added reference image: https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/5dd13496-a72d-47a4-b22f-ff532de6951b.jpg
Added reference image: https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/8b24290e-aa26-4a0b-a233-9d9853379a87.jpg
Added reference image: https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/289c4643-a4dc-41c9-aa61-c530cc8ae54d.jpg
Added reference image: https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/35582783-14bc-43c1-8b9e-51014de65dae.jpeg
Added reference image: https://qxripdllxckfpnimzxoa.supabase.co/storage/v1/object/public/dataset-images/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/b41a931d-b0ab-4bdf-8d7b-cec89f568f5d.jpeg
```

---

## Test 3: Cafe Exterior (9:16)

### Request:
```json
{
  "prompt": "outdoor cafe seating with bistro chairs and a menu board",
  "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
  "aspect_ratio": "9:16"
}
```

### Expected Result:
- Vertical image for Instagram Stories
- Parisian-style bistro chairs (black and cream checkered)
- Menu board similar to BRAUN NOTES COFFEE
- Sophisticated urban atmosphere

### Actual Response:
```json
PASTE_RESPONSE_HERE
```

---

## Test 4: Pastry Photo (4:3)

### Request:
```json
{
  "prompt": "a chocolate croissant on a plate with coffee in the background",
  "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
  "style": "Food Photography",
  "aspect_ratio": "4:3"
}
```

### Expected Result:
- Food photography style
- Warm, cozy cafe aesthetic
- Soft bokeh background
- Similar plating and composition to dataset

### Actual Response:
```json
PASTE_RESPONSE_HERE
```

---

## Test 5: Social Media Banner (16:9)

### Request:
```json
{
  "prompt": "coffee shop interior with espresso machine and pastries",
  "dataset_id": "d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a",
  "aspect_ratio": "16:9"
}
```

### Expected Result:
- Wide banner format
- Professional espresso machine
- Dark wood counter
- Warm interior lighting

### Actual Response:
```json
PASTE_RESPONSE_HERE
```

---

## Comparison: Test 1 vs Test 2

### Visual Differences:
- [ ] Test 2 matches cafe color palette (brown, cream, black)
- [ ] Test 2 has warmer, more natural lighting
- [ ] Test 2 shows similar marble table texture
- [ ] Test 2 has cozy, sophisticated atmosphere
- [ ] Test 2 matches bistro aesthetic

### Technical Differences:
- Test 1: No reference images used
- Test 2: 5 reference images downloaded and used
- Test 2: Longer, more detailed prompt with style context

---

## Performance Metrics

| Test | Generation Time | Image Download Time | Total Time | Success |
|------|----------------|---------------------|------------|---------|
| Test 1 (no dataset) | ? seconds | 0 seconds | ? seconds | ✅/❌ |
| Test 2 (with dataset) | ? seconds | ? seconds | ? seconds | ✅/❌ |
| Test 3 | ? seconds | ? seconds | ? seconds | ✅/❌ |
| Test 4 | ? seconds | ? seconds | ? seconds | ✅/❌ |
| Test 5 | ? seconds | ? seconds | ? seconds | ✅/❌ |

---

## Troubleshooting

### If Tests Fail:

1. **Check server is running:**
   ```bash
   curl http://localhost:8000/
   ```

2. **Check dependencies installed:**
   ```bash
   pip list | grep -E "pillow|requests|google-generativeai"
   ```

3. **Check server logs for errors:**
   - Look for "Added reference image" messages
   - Check for download errors
   - Verify Gemini API calls

4. **Verify dataset exists:**
   ```bash
   curl http://localhost:8000/ai/dataset/d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a/images
   ```

---

## Conclusion

### What Worked:
- FILL IN AFTER TESTING

### What Didn't Work:
- FILL IN AFTER TESTING

### Style Consistency:
- FILL IN AFTER TESTING

### Recommendations:
- FILL IN AFTER TESTING

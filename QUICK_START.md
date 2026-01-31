# 🚀 Quick Start - Nano Banana Image Generation

## ✅ What's Already Done (via Supabase MCP)

1. ✅ Database: `datasets.user_id` is now nullable
2. ✅ Storage Policies: All 4 policies created
3. ✅ Code: Updated to Nano Banana (Gemini 2.5 Flash Image)
4. ✅ Dependencies: Updated (removed pillow)

---

## ⚠️ ONE STEP TO COMPLETE

### Create Storage Bucket (30 seconds)

1. Go to: https://supabase.com/dashboard/project/qxripdllxckfpnimzxoa/storage/buckets
2. Click "New bucket"
3. Name: `generated-images`
4. Public: **Yes** ✅
5. Click "Create"

**That's it!** The policies are already set up via MCP.

---

## 🧪 Test It

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Restart server
uvicorn app.main:app --reload

# 3. Test generation
curl -X POST http://localhost:8000/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a cute puppy",
    "aspect_ratio": "1:1"
  }'
```

---

## 📊 Supported Aspect Ratios

- `1:1` - Square (1024x1024)
- `16:9` - Widescreen (1344x768)
- `9:16` - Vertical (768x1344)
- `4:3` - Standard (1184x864)
- `3:4` - Portrait (864x1184)
- `2:3`, `3:2`, `4:5`, `5:4`, `21:9`

---

## 📚 Full Documentation

- **Setup Guide:** `NANO_BANANA_SETUP.md`
- **Complete Status:** `SETUP_COMPLETE.md`
- **API Docs:** `FRONTEND_INTEGRATION.md`

---

## 🎉 You're Almost Done!

Just create the bucket and you're ready to generate images! 🍌

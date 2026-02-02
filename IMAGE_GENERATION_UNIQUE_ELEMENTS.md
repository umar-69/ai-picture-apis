# Image Generation with Unique Visual Elements

## Overview
The image generation API now intelligently extracts and incorporates unique visual elements from your dataset images to create consistent, brand-aligned generated images.

## How It Works

### 1. Dataset Analysis Extraction
When you provide a `dataset_id`, the API:
- Fetches up to 5 analyzed images from the dataset
- Extracts **unique visual elements** from the `tags` field (e.g., "Marble Countertop", "Edison Bulbs", "Exposed Brick")
- Collects additional style information: vibe, lighting, colors
- Downloads actual reference images to provide visual context

### 2. Unique Element Processing
```python
# Extracts all tags from analyzed images
all_tags = ["Marble Countertop", "Edison Bulbs", "Edison Bulbs", "Warm Lighting", "Marble Countertop"]

# Counts frequency and ranks by popularity
tag_counts = Counter(all_tags)
# Result: [("Marble Countertop", 2), ("Edison Bulbs", 2), ("Warm Lighting", 1)]

# Gets top 10 unique elements
unique_visual_elements = ["Marble Countertop", "Edison Bulbs", "Warm Lighting", ...]
```

### 3. System Instruction Prompt
The API builds a structured prompt that matches your TypeScript service format:

**With Dataset (Recommended):**
```
TASK: Generate a photorealistic professional marketing image for this specific brand location.
STYLE: Strictly replicate the interior design, textures, lighting, and layout seen in the provided reference images.
UNIQUE ELEMENTS TO INCLUDE: Marble Countertop, Edison Bulbs, Exposed Brick, Industrial Pipes, Warm Neon, Wooden Beams, Concrete Floors, Vintage Furniture
UNIQUE VISUAL ELEMENTS: Marble Countertop, Edison Bulbs, Exposed Brick, Industrial Pipes, Warm Neon, Wooden Beams, Concrete Floors, Vintage Furniture. 
Vibe: Industrial, Cozy, Modern. 
Lighting: Warm ambient, Natural light. 
Colors: Earth tones, Warm browns, Gray concrete. 
Strictly replicate the interior design, textures, materials, and layout seen in the 5 reference image(s). 
SCENE: A coffee shop interior with customers enjoying their drinks
ADDITIONAL STYLE: Cinematic
```

**Without Dataset (Fallback):**
```
Brand: My Coffee Shop. Vibe: Cozy. Theme: Modern Industrial. A coffee shop interior with customers enjoying their drinks. Style: Cinematic.
```

## Code Changes Explained

### What Changed
Updated `/ai/generate` endpoint in `app/routers/ai.py`:

#### 1. Extract Unique Visual Elements (Lines 73-116)
```python
# Extract specific visual elements from tags (these are the unique tangible elements)
if 'tags' in analysis and isinstance(analysis['tags'], list):
    all_tags.extend(analysis['tags'])

# Extract vibe, lighting, and colors for additional context
if 'vibe' in analysis:
    vibes.append(analysis['vibe'])
if 'lighting' in analysis:
    lighting_styles.append(analysis['lighting'])
if 'colors' in analysis:
    colors.append(analysis['colors'])

# Count frequency and get unique elements
from collections import Counter
tag_counts = Counter(all_tags)
unique_visual_elements = [tag for tag, count in tag_counts.most_common(10)]
```

**Why:** This extracts the specific, tangible visual elements (like "Marble Countertop", "Edison Bulbs") that were identified during the fast analysis. These are the distinctive features that define your brand's visual identity.

**How it helps:** Instead of generic style descriptions, the AI gets concrete elements to include in the generated image, ensuring consistency with your dataset.

#### 2. Build Comprehensive Dataset Context (Lines 118-135)
```python
# Build comprehensive dataset context with unique elements
if unique_visual_elements:
    dataset_context += f"UNIQUE VISUAL ELEMENTS: {', '.join(unique_visual_elements)}. "

if vibes:
    unique_vibes = list(set(vibes))
    dataset_context += f"Vibe: {', '.join(unique_vibes)}. "

if lighting_styles:
    unique_lighting = list(set(lighting_styles))
    dataset_context += f"Lighting: {', '.join(unique_lighting)}. "

if colors:
    unique_colors = list(set(colors))
    dataset_context += f"Colors: {', '.join(unique_colors)}. "

if reference_images:
    dataset_context += f"Strictly replicate the interior design, textures, materials, and layout seen in the {len(reference_images)} reference image(s). "
```

**Why:** Organizes all the extracted information into a structured context that emphasizes the unique elements first, followed by supporting style information.

**How it helps:** Provides the AI with a clear hierarchy of what's most important (unique elements) vs. supporting details (vibe, lighting, colors).

#### 3. System Instruction Format (Lines 141-161)
```python
if reference_images and unique_visual_elements:
    # Build system instruction with unique visual elements
    system_instruction = f"""TASK: Generate a photorealistic professional marketing image for this specific brand location.
STYLE: Strictly replicate the interior design, textures, lighting, and layout seen in the provided reference images.
UNIQUE ELEMENTS TO INCLUDE: {', '.join(unique_visual_elements[:8])}
{dataset_context}
SCENE: {request.prompt}"""
    
    if request.style:
        system_instruction += f"\nADDITIONAL STYLE: {request.style}"
    
    full_prompt = system_instruction
else:
    # Fallback to simpler prompt if no dataset
    style_suffix = ""
    if request.style:
        style_suffix = f" Style: {request.style}."
    
    full_prompt = f"{business_context}{dataset_context}{request.prompt}{style_suffix}".strip()
```

**Why:** Creates a structured, task-oriented prompt that matches your TypeScript service format. The prompt explicitly tells the AI to:
1. Generate a professional marketing image
2. Replicate the style from reference images
3. Include specific unique elements
4. Create the requested scene

**How it helps:** This structured format is more effective than a simple concatenated string. It gives the AI clear instructions in a format that Gemini 3 Pro understands well.

## Example Usage

### Request
```json
{
  "prompt": "A barista making coffee behind the counter",
  "dataset_id": "abc-123-def",
  "aspect_ratio": "16:9",
  "style": "Cinematic"
}
```

### What Happens Behind the Scenes

1. **Fetch Dataset Images:**
   - Gets 5 analyzed images from dataset `abc-123-def`
   - Each has analysis with tags like:
     - Image 1: `["Marble Countertop", "Edison Bulbs", "Exposed Brick"]`
     - Image 2: `["Edison Bulbs", "Industrial Pipes", "Wooden Beams"]`
     - Image 3: `["Marble Countertop", "Concrete Floors", "Vintage Furniture"]`

2. **Extract Unique Elements:**
   - Combines all tags: `["Marble Countertop", "Edison Bulbs", "Exposed Brick", "Edison Bulbs", "Industrial Pipes", ...]`
   - Counts frequency: `{"Marble Countertop": 2, "Edison Bulbs": 2, "Exposed Brick": 1, ...}`
   - Gets top 10: `["Marble Countertop", "Edison Bulbs", "Industrial Pipes", ...]`

3. **Build System Instruction:**
   ```
   TASK: Generate a photorealistic professional marketing image for this specific brand location.
   STYLE: Strictly replicate the interior design, textures, lighting, and layout seen in the provided reference images.
   UNIQUE ELEMENTS TO INCLUDE: Marble Countertop, Edison Bulbs, Industrial Pipes, Exposed Brick, Wooden Beams, Concrete Floors, Vintage Furniture, Warm Neon
   UNIQUE VISUAL ELEMENTS: Marble Countertop, Edison Bulbs, Industrial Pipes, Exposed Brick, Wooden Beams, Concrete Floors, Vintage Furniture, Warm Neon. 
   Vibe: Industrial, Cozy. 
   Lighting: Warm ambient lighting, Natural light. 
   Colors: Earth tones, Warm browns, Gray concrete. 
   Strictly replicate the interior design, textures, materials, and layout seen in the 5 reference image(s). 
   SCENE: A barista making coffee behind the counter
   ADDITIONAL STYLE: Cinematic
   ```

4. **Generate Image:**
   - Sends prompt + 5 reference images to Gemini 3 Pro
   - AI generates image incorporating the unique elements
   - Returns consistent, brand-aligned image

## Benefits

### ✅ Consistency
Generated images include the same unique visual elements from your dataset, ensuring brand consistency.

### ✅ Specificity
Instead of vague descriptions, the AI gets concrete elements like "Marble Countertop" or "Edison Bulbs".

### ✅ Frequency-Based Prioritization
Most common elements appear first, ensuring the most defining features are emphasized.

### ✅ Visual + Textual Context
Combines actual reference images with extracted text descriptions for maximum accuracy.

### ✅ Structured Prompting
Uses a clear task-oriented format that Gemini 3 Pro understands well.

## Comparison: Before vs After

### Before
```
A coffee shop interior with customers enjoying their drinks. Style: Cinematic.
```
❌ Generic, no specific brand elements
❌ AI has to guess what style means
❌ Inconsistent results

### After
```
TASK: Generate a photorealistic professional marketing image for this specific brand location.
STYLE: Strictly replicate the interior design, textures, lighting, and layout seen in the provided reference images.
UNIQUE ELEMENTS TO INCLUDE: Marble Countertop, Edison Bulbs, Industrial Pipes, Exposed Brick, Wooden Beams, Concrete Floors, Vintage Furniture, Warm Neon
UNIQUE VISUAL ELEMENTS: Marble Countertop, Edison Bulbs, Industrial Pipes, Exposed Brick, Wooden Beams, Concrete Floors, Vintage Furniture, Warm Neon. 
Vibe: Industrial, Cozy. 
Lighting: Warm ambient lighting, Natural light. 
Colors: Earth tones, Warm browns, Gray concrete. 
Strictly replicate the interior design, textures, materials, and layout seen in the 5 reference image(s). 
SCENE: A coffee shop interior with customers enjoying their drinks
ADDITIONAL STYLE: Cinematic
```
✅ Specific unique elements listed
✅ Clear task and style instructions
✅ Visual references included
✅ Consistent, brand-aligned results

## Workflow

1. **Upload & Analyze Dataset**
   ```bash
   POST /ai/dataset/analyze-fast
   # Analyzes images and extracts unique visual elements
   ```

2. **Mark as Trained** (Optional)
   ```bash
   PATCH /ai/dataset/{dataset_id}/training-status
   # Mark dataset as ready for generation
   ```

3. **Generate Images**
   ```bash
   POST /ai/generate
   {
     "prompt": "Your scene description",
     "dataset_id": "your-dataset-id",
     "aspect_ratio": "16:9"
   }
   # Generates images using unique elements from dataset
   ```

## Technical Notes

- **Top 10 Elements**: Uses the 10 most common unique elements (can be adjusted)
- **Top 8 in Prompt**: Includes up to 8 elements in the main system instruction
- **5 Reference Images**: Downloads up to 5 actual images as visual references
- **Frequency Ranking**: More common elements appear first
- **Fallback Support**: Works without dataset (uses simpler prompt)

## Next Steps

The API is now ready to generate brand-consistent images! The system will:
1. Extract unique visual elements from your analyzed dataset
2. Build a structured system instruction prompt
3. Include reference images for visual context
4. Generate images that match your brand's unique style

🚀 **Ready to use immediately!**

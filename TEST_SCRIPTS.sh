#!/bin/bash

# Test Scripts for Nano Banana Image Generation with Real Supabase Data
# Dataset: Coffee Shop (BRAUN NOTES COFFEE)
# Dataset ID: d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a
# Images: 11 cafe/coffee images with analyzed style

echo "=========================================="
echo "Nano Banana Image Generation Tests"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base URL (change to your deployed URL if needed)
BASE_URL="http://localhost:8000"

echo -e "${BLUE}Base URL: ${BASE_URL}${NC}"
echo ""

# Real dataset from Supabase
DATASET_ID="d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a"
DATASET_NAME="Coffee Shop (BRAUN NOTES COFFEE)"
IMAGE_COUNT="11"

echo -e "${GREEN}Using Real Dataset:${NC}"
echo "  Dataset ID: ${DATASET_ID}"
echo "  Dataset Name: ${DATASET_NAME}"
echo "  Images: ${IMAGE_COUNT} cafe/coffee images"
echo "  Style: Cozy, sophisticated European bistro atmosphere"
echo "  Colors: Deep brown, cream, black, golden tan"
echo "  Lighting: Soft, warm, natural indoor lighting"
echo ""

# Test 1: Generate WITHOUT dataset (text-only context)
echo -e "${YELLOW}Test 1: Generate WITHOUT Dataset (Text-Only)${NC}"
echo "This will generate a generic coffee cup image with no style reference"
echo ""
echo "Command:"
echo "curl -X POST ${BASE_URL}/ai/generate \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"prompt\": \"a latte with heart-shaped latte art on a marble table\","
echo "    \"style\": \"Photorealistic\","
echo "    \"aspect_ratio\": \"1:1\""
echo "  }'"
echo ""
read -p "Press Enter to run Test 1..."

curl -X POST "${BASE_URL}/ai/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a latte with heart-shaped latte art on a marble table",
    "style": "Photorealistic",
    "aspect_ratio": "1:1"
  }' | jq '.'

echo ""
echo "---"
echo ""

# Test 2: Generate WITH dataset (visual + text context)
echo -e "${YELLOW}Test 2: Generate WITH Dataset (Visual Context)${NC}"
echo "This will use 5 reference images from the coffee shop dataset"
echo "Expected: Image matching the cozy European cafe style"
echo ""
echo "Command:"
echo "curl -X POST ${BASE_URL}/ai/generate \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"prompt\": \"a latte with heart-shaped latte art on a marble table\","
echo "    \"dataset_id\": \"${DATASET_ID}\","
echo "    \"style\": \"Photorealistic\","
echo "    \"aspect_ratio\": \"1:1\""
echo "  }'"
echo ""
read -p "Press Enter to run Test 2..."

curl -X POST "${BASE_URL}/ai/generate" \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"a latte with heart-shaped latte art on a marble table\",
    \"dataset_id\": \"${DATASET_ID}\",
    \"style\": \"Photorealistic\",
    \"aspect_ratio\": \"1:1\"
  }" | jq '.'

echo ""
echo "---"
echo ""

# Test 3: Generate cafe exterior matching dataset style
echo -e "${YELLOW}Test 3: Cafe Exterior (Matching Dataset Style)${NC}"
echo "Generate an outdoor cafe scene matching the bistro chair style"
echo ""
echo "Command:"
echo "curl -X POST ${BASE_URL}/ai/generate \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"prompt\": \"outdoor cafe seating with bistro chairs and a menu board\","
echo "    \"dataset_id\": \"${DATASET_ID}\","
echo "    \"aspect_ratio\": \"9:16\""
echo "  }'"
echo ""
read -p "Press Enter to run Test 3..."

curl -X POST "${BASE_URL}/ai/generate" \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"outdoor cafe seating with bistro chairs and a menu board\",
    \"dataset_id\": \"${DATASET_ID}\",
    \"aspect_ratio\": \"9:16\"
  }" | jq '.'

echo ""
echo "---"
echo ""

# Test 4: Generate pastry matching dataset style
echo -e "${YELLOW}Test 4: Pastry Photo (Matching Dataset Style)${NC}"
echo "Generate a pastry photo matching the warm, cozy cafe aesthetic"
echo ""
echo "Command:"
echo "curl -X POST ${BASE_URL}/ai/generate \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"prompt\": \"a chocolate croissant on a plate with coffee in the background\","
echo "    \"dataset_id\": \"${DATASET_ID}\","
echo "    \"style\": \"Food Photography\","
echo "    \"aspect_ratio\": \"4:3\""
echo "  }'"
echo ""
read -p "Press Enter to run Test 4..."

curl -X POST "${BASE_URL}/ai/generate" \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"a chocolate croissant on a plate with coffee in the background\",
    \"dataset_id\": \"${DATASET_ID}\",
    \"style\": \"Food Photography\",
    \"aspect_ratio\": \"4:3\"
  }" | jq '.'

echo ""
echo "---"
echo ""

# Test 5: Wide banner for social media
echo -e "${YELLOW}Test 5: Social Media Banner (16:9)${NC}"
echo "Generate a wide banner for social media matching cafe style"
echo ""
echo "Command:"
echo "curl -X POST ${BASE_URL}/ai/generate \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"prompt\": \"coffee shop interior with espresso machine and pastries\","
echo "    \"dataset_id\": \"${DATASET_ID}\","
echo "    \"aspect_ratio\": \"16:9\""
echo "  }'"
echo ""
read -p "Press Enter to run Test 5..."

curl -X POST "${BASE_URL}/ai/generate" \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"coffee shop interior with espresso machine and pastries\",
    \"dataset_id\": \"${DATASET_ID}\",
    \"aspect_ratio\": \"16:9\"
  }" | jq '.'

echo ""
echo "=========================================="
echo "Tests Complete!"
echo "=========================================="
echo ""
echo -e "${GREEN}What to Check:${NC}"
echo "1. Test 1 (no dataset) should produce a generic latte image"
echo "2. Test 2 (with dataset) should match the cozy European cafe style"
echo "3. Compare image_url from both tests to see the difference"
echo "4. Check server logs for 'Using 5 reference images from dataset'"
echo ""
echo -e "${BLUE}Expected Server Logs:${NC}"
echo "  Generating image with Nano Banana. Prompt: ..."
echo "  Using 5 reference images from dataset"
echo "  Added reference image: https://qxripdllxckfpnimzxoa.supabase.co/storage/..."
echo ""

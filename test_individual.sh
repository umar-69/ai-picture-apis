#!/bin/bash

# Individual Test Scripts - Run one at a time

# Dataset Info
DATASET_ID="d3bfce6e-75fb-4b2b-a7a1-7d14b3dd9c7a"
BASE_URL="http://localhost:8000"

echo "Individual Test Scripts for Nano Banana"
echo "Dataset: Coffee Shop (11 images)"
echo ""
echo "Choose a test:"
echo "1. Generate WITHOUT dataset (generic)"
echo "2. Generate WITH dataset (style-matched)"
echo "3. Cafe exterior with bistro chairs"
echo "4. Pastry food photography"
echo "5. Wide social media banner"
echo ""
read -p "Enter test number (1-5): " test_num

case $test_num in
  1)
    echo "Test 1: Generic latte (no dataset)"
    curl -X POST "${BASE_URL}/ai/generate" \
      -H "Content-Type: application/json" \
      -d '{
        "prompt": "a latte with heart-shaped latte art on a marble table",
        "style": "Photorealistic",
        "aspect_ratio": "1:1"
      }' | jq '.'
    ;;
  2)
    echo "Test 2: Style-matched latte (with dataset)"
    curl -X POST "${BASE_URL}/ai/generate" \
      -H "Content-Type: application/json" \
      -d "{
        \"prompt\": \"a latte with heart-shaped latte art on a marble table\",
        \"dataset_id\": \"${DATASET_ID}\",
        \"style\": \"Photorealistic\",
        \"aspect_ratio\": \"1:1\"
      }" | jq '.'
    ;;
  3)
    echo "Test 3: Cafe exterior"
    curl -X POST "${BASE_URL}/ai/generate" \
      -H "Content-Type: application/json" \
      -d "{
        \"prompt\": \"outdoor cafe seating with bistro chairs and a menu board\",
        \"dataset_id\": \"${DATASET_ID}\",
        \"aspect_ratio\": \"9:16\"
      }" | jq '.'
    ;;
  4)
    echo "Test 4: Pastry photo"
    curl -X POST "${BASE_URL}/ai/generate" \
      -H "Content-Type: application/json" \
      -d "{
        \"prompt\": \"a chocolate croissant on a plate with coffee in the background\",
        \"dataset_id\": \"${DATASET_ID}\",
        \"style\": \"Food Photography\",
        \"aspect_ratio\": \"4:3\"
      }" | jq '.'
    ;;
  5)
    echo "Test 5: Social media banner"
    curl -X POST "${BASE_URL}/ai/generate" \
      -H "Content-Type: application/json" \
      -d "{
        \"prompt\": \"coffee shop interior with espresso machine and pastries\",
        \"dataset_id\": \"${DATASET_ID}\",
        \"aspect_ratio\": \"16:9\"
      }" | jq '.'
    ;;
  *)
    echo "Invalid test number"
    exit 1
    ;;
esac

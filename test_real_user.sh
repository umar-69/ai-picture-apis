#!/bin/bash
# Real user test for utahirb@gmail.com
# Run when Supabase rate limit has reset (usually a few minutes)

BASE_URL="https://ai-picture-apis.onrender.com"
EMAIL="utahirb@gmail.com"
PASSWORD="f4U1ebgzsnNSUjyT"  # Randomly generated, save this!

echo "=== 1. Signup ==="
SIGNUP_RESP=$(curl -s -X POST "$BASE_URL/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"metadata\":{\"full_name\":\"Umar Tahir Butt\",\"source\":\"api_test\"}}")
echo "$SIGNUP_RESP" | jq .

if echo "$SIGNUP_RESP" | jq -e '.user.id' >/dev/null 2>&1; then
  echo -e "\n=== 2. Login ==="
  LOGIN_RESP=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
  echo "$LOGIN_RESP" | jq .
  
  TOKEN=$(echo "$LOGIN_RESP" | jq -r '.access_token // empty')
  if [ -n "$TOKEN" ]; then
    echo -e "\n=== 3. Get profile (GET /users/me) ==="
    curl -s -X GET "$BASE_URL/users/me" -H "Authorization: Bearer $TOKEN" | jq .
    
    echo -e "\n=== 4. Create business profile ==="
    curl -s -X POST "$BASE_URL/business/" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"business_name":"Test Business","theme":"modern","target_audience":"developers"}' | jq .
  fi
else
  echo -e "\nSignup failed. Trying login (in case user already exists)..."
  LOGIN_RESP=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
  echo "$LOGIN_RESP" | jq .
  TOKEN=$(echo "$LOGIN_RESP" | jq -r '.access_token // empty')
  if [ -n "$TOKEN" ]; then
    echo -e "\n=== Get profile (GET /users/me) ==="
    curl -s -X GET "$BASE_URL/users/me" -H "Authorization: Bearer $TOKEN" | jq .
    echo -e "\n=== Create business profile ==="
    curl -s -X POST "$BASE_URL/business/" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"business_name":"Test Business","theme":"modern","target_audience":"developers"}' | jq .
  fi
fi

echo -e "\n--- Credentials (save these) ---"
echo "Email: $EMAIL"
echo "Password: $PASSWORD"

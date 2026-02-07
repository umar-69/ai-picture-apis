#!/bin/bash
# Disable email confirmation for Supabase Auth
# Users will be auto-confirmed on signup - no verification email sent
#
# EASIEST: Supabase Dashboard (no token needed)
#   https://supabase.com/dashboard/project/qxripdllxckfpnimzxoa/auth/providers
#   Click Email → turn OFF "Confirm email" → Save
#
# OR via API (requires token from https://supabase.com/dashboard/account/tokens):
#   SUPABASE_ACCESS_TOKEN="your-token" ./disable_email_confirmation.sh

PROJECT_REF="qxripdllxckfpnimzxoa"  # From your project URL

if [ -z "$SUPABASE_ACCESS_TOKEN" ]; then
  echo "Error: Set SUPABASE_ACCESS_TOKEN from https://supabase.com/dashboard/account/tokens"
  exit 1
fi

echo "Disabling email confirmation..."

curl -s -X PATCH "https://api.supabase.com/v1/projects/$PROJECT_REF/config/auth" \
  -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mailer_autoconfirm": true}' | jq .

echo ""
echo "Done. Signups will now auto-confirm without email verification."

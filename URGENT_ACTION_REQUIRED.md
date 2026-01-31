# 🚨 URGENT: Configuration Mismatch Detected

## Problem

Your **frontend/mobile apps are using PRODUCTION Supabase** (`qxripdllxckfpnimzxoa`), but I initially configured the backend API to use the **DEV environment** (`fxrygwdyysakwsfcjjts`).

This means:
- Frontend uploads would go to PROD database
- Backend API was trying to read from DEV database (which is empty)
- Data mismatch between frontend and backend

## What I've Done

1. ✅ **Reverted backend to use PRODUCTION** - `app/config.py` now uses PROD URL and PROD anon key
2. ⚠️ **Database migration still needed** - The `datasets.user_id` column needs to be made nullable in PROD

## What You Need to Do

### Option 1: Run SQL Migration on PROD (Recommended)

Go to your Supabase PROD dashboard and run this SQL:

```sql
-- Make user_id nullable to support anonymous uploads
ALTER TABLE datasets ALTER COLUMN user_id DROP NOT NULL;
```

**How to run:**
1. Go to https://supabase.com/dashboard/project/qxripdllxckfpnimzxoa
2. Click "SQL Editor" in the left sidebar
3. Paste the SQL above
4. Click "Run"

### Option 2: Add PROD Service Role Key to .env

If you want to use the MCP tool to run migrations on PROD, add this to your `.env`:

```bash
SUPABASE_SERVICE_ROLE_KEY_PROD="your-prod-service-role-key-here"
```

**Where to find it:**
1. Go to https://supabase.com/dashboard/project/qxripdllxckfpnimzxoa/settings/api
2. Look for "service_role" key (starts with `eyJ...`)
3. Copy it and add to `.env`

---

## Current Configuration Status

### ✅ Fixed:
- Backend now uses PROD Supabase URL: `https://qxripdllxckfpnimzxoa.supabase.co`
- Backend uses PROD anon key (matches frontend)
- Gemini model updated to `gemini-3-flash-preview` with Agentic Vision
- Dataset auto-creation logic added

### ⚠️ Still Needs Fixing:
- **PROD database:** `datasets.user_id` must be nullable
- Without this, anonymous uploads will fail with FK constraint error

---

## Testing After Migration

Once you run the SQL migration on PROD, test:

1. **Anonymous upload:** Upload images without authentication
2. **Authenticated upload:** Upload images with valid JWT token
3. **Verify:** Check that datasets are created automatically

---

## Quick Reference

**PROD Supabase:**
- URL: `https://qxripdllxckfpnimzxoa.supabase.co`
- Anon Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF4cmlwZGxseGNrZnBuaW16eG9hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk3MTI5MTcsImV4cCI6MjA4NTI4ODkxN30.M73mLVPBugMrdaUGMGlfKaOHmX1zLmGHax-GeIEnou4`
- Database: `postgresql://postgres:[YOUR-PASSWORD]@db.qxripdllxckfpnimzxoa.supabase.co:5432/postgres`

**DEV Supabase (not currently used):**
- URL: `https://fxrygwdyysakwsfcjjts.supabase.co`
- Anon Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ4cnlnd2R5eXNha3dzZmNqanRzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxNTc3NzcsImV4cCI6MjA3MjczMzc3N30.JOH37wG58CURvjXv4mSUb_tI6ansnYn9_v4ahs9V8mE`

---

## Summary

**Action Required:** Run the SQL migration on PROD to make `datasets.user_id` nullable.

**Why:** This allows anonymous users to upload images without having a user account, which is essential for your "free tries" feature.

**How Long:** Takes 5 seconds to run the SQL in Supabase dashboard.

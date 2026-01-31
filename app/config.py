import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Supabase configuration
# IMPORTANT: Using PRODUCTION environment to match frontend/mobile apps
SUPABASE_URL = os.getenv("SUPABASE_URL")  # PROD: https://qxripdllxckfpnimzxoa.supabase.co
SUPABASE_URL_DEV = os.getenv("SUPABASE_URL_DEV")  # DEV: https://fxrygwdyysakwsfcjjts.supabase.co

# Anon key for client operations (JWT format - this is what Supabase client expects)
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  # PROD anon key
SUPABASE_ANON_KEY_DEV = os.getenv("SUPABSE_DEV_KEY")  # DEV anon key

# Service key for backend operations
# The sbp_ format is for server-side SDKs, not the Python client which expects JWT tokens
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # sbp_ format (not used)

# Service Role Key (JWT format) - for DEV environment only
# NOTE: We don't have a PROD service role key in .env, so we'll use anon key for PROD
SUPABASE_SERVICE_ROLE_KEY_DEV = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # DEV service role

# IMPORTANT: The Supabase Python client requires a JWT token
# For PROD: Using anon key (RLS is disabled on tables, so anon key has full access)
# For DEV: Could use service role key, but we're on PROD
SUPABASE_KEY = SUPABASE_ANON_KEY  # Use PROD anon key
SUPABASE_SERVICE_ROLE_KEY = SUPABASE_ANON_KEY  # Use anon key as "service role" for PROD

# Database settings
DB_POOL_SIZE = 5
DB_TIMEOUT = 30 

GCP_PROJECT_ID=os.getenv("GCP_PROJECT_ID")
GCS_BUCKET_NAME=os.getenv("GCS_BUCKET_NAME")
GCP_CLIENT_EMAIL=os.getenv("GCP_CLIENT_EMAIL")
GCP_PRIVATE_KEY=os.getenv("GCP_PRIVATE_KEY")

# Stripe configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_TEST_SECRET_KEY = os.getenv("STRIPE_TEST_SECRET_KEY")
STRIPE_TEST_PUBLISHABLE_KEY = os.getenv("STRIPE_TEST_PUBLISHABLE_KEY")
STRIPE_TEST_WEBHOOK_SECRET = os.getenv("STRIPE_TEST_WEBHOOK_SECRET")
STRIPE_API_VERSION = "2019-09-09"
STRIPE_APPLE_PAY_MERCHANT_ID = os.getenv("STRIPE_APPLE_PAY_MERCHANT_ID")
STRIPE_GOOGLE_PAY_MERCHANT_ID = os.getenv("STRIPE_GOOGLE_PAY_MERCHANT_ID")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")

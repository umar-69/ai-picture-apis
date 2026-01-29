import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_URL_DEV = os.getenv("SUPABASE_URL_DEV")

# Anon key for client operations (JWT format - this is what Supabase client expects)
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABSE_DEV_KEY = os.getenv("SUPABSE_DEV_KEY")
# Service key for backend operations (Note: This format is not a JWT and won't work with Supabase Python client)
# The sbp_ format is for server-side SDKs, not the Python client which expects JWT tokens
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
# This is the actual JWT service role key found in the snippet
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# IMPORTANT: The Supabase Python client requires a JWT token, not the sbp_ format service key
# Using anon key for all operations as it's in the correct JWT format
# With RLS disabled on your tables, the anon key will work for all CRUD operations
SUPABASE_KEY = SUPABASE_ANON_KEY  # Always use anon key which is in JWT format
SUPABASE_DEV_KEY = SUPABSE_DEV_KEY

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

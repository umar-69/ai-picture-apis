#!/usr/bin/env python3
"""
Quick configuration test script to verify Supabase setup
"""
import os
from dotenv import load_dotenv
import jwt

load_dotenv()

def decode_jwt_without_verify(token):
    """Decode JWT without verification to inspect payload"""
    try:
        # Decode without verification (just to inspect)
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=" * 60)
    print("SUPABASE CONFIGURATION TEST")
    print("=" * 60)
    
    # URLs
    prod_url = os.getenv("SUPABASE_URL")
    dev_url = os.getenv("SUPABASE_URL_DEV")
    
    print(f"\n📍 URLs:")
    print(f"  PROD: {prod_url}")
    print(f"  DEV:  {dev_url}")
    
    # Keys
    prod_anon = os.getenv("SUPABASE_ANON_KEY")
    dev_anon = os.getenv("SUPABSE_DEV_KEY")
    service_role = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    print(f"\n🔑 Keys:")
    print(f"  PROD Anon Key: {prod_anon[:20]}...")
    print(f"  DEV Anon Key:  {dev_anon[:20]}...")
    print(f"  Service Role:  {service_role[:20]}...")
    
    # Decode JWTs
    print(f"\n🔍 JWT Analysis:")
    
    print(f"\n  PROD Anon Key:")
    prod_decoded = decode_jwt_without_verify(prod_anon)
    print(f"    ref: {prod_decoded.get('ref', 'N/A')}")
    print(f"    role: {prod_decoded.get('role', 'N/A')}")
    
    print(f"\n  DEV Anon Key:")
    dev_decoded = decode_jwt_without_verify(dev_anon)
    print(f"    ref: {dev_decoded.get('ref', 'N/A')}")
    print(f"    role: {dev_decoded.get('role', 'N/A')}")
    
    print(f"\n  Service Role Key:")
    service_decoded = decode_jwt_without_verify(service_role)
    print(f"    ref: {service_decoded.get('ref', 'N/A')}")
    print(f"    role: {service_decoded.get('role', 'N/A')}")
    
    # Check matches
    print(f"\n✅ Configuration Check:")
    
    dev_ref = dev_decoded.get('ref', '')
    service_ref = service_decoded.get('ref', '')
    
    if dev_ref in dev_url and service_ref in dev_url:
        print(f"  ✓ DEV URL matches DEV anon key")
        print(f"  ✓ DEV URL matches service role key")
        print(f"  ✓ Configuration is CORRECT for DEV environment")
    else:
        print(f"  ✗ Configuration mismatch detected!")
        print(f"    DEV URL: {dev_url}")
        print(f"    DEV Key ref: {dev_ref}")
        print(f"    Service Key ref: {service_ref}")
    
    # Current config
    from app.config import SUPABASE_URL, SUPABASE_KEY
    print(f"\n📋 Current App Configuration:")
    print(f"  Using URL: {SUPABASE_URL}")
    print(f"  Using Key: {SUPABASE_KEY[:20]}...")
    
    if SUPABASE_URL == dev_url:
        print(f"  ✓ App is using DEV environment")
    else:
        print(f"  ⚠ App is using PROD environment")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

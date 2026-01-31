from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# Initialize Admin Supabase client (Service Role)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def get_supabase() -> Client:
    return supabase

def get_supabase_admin() -> Client:
    return supabase_admin

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), client: Client = Depends(get_supabase)):
    token = credentials.credentials
    try:
        # Verify the token using Supabase
        # get_user returns the user object if the token is valid
        response = client.auth.get_user(token)
        if not response or not response.user:
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return response.user
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Could not validate credentials: {str(e)}")

def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security_optional), client: Client = Depends(get_supabase)):
    if not credentials:
        return None
    token = credentials.credentials
    try:
        response = client.auth.get_user(token)
        if not response or not response.user:
             return None
        return response.user
    except Exception:
        return None

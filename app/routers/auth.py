from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas import UserSignup, UserLogin
from app.dependencies import get_supabase
from supabase import Client

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/signup")
def signup(user: UserSignup, supabase: Client = Depends(get_supabase)):
    try:
        # Check if user already exists (optional, supabase handles this but we can wrap)
        res = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password,
            "options": {
                "data": user.metadata or {}
            }
        })
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login(user: UserLogin, supabase: Client = Depends(get_supabase)):
    try:
        res = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/logout")
def logout(supabase: Client = Depends(get_supabase)):
    try:
        # Since we are using JWTs, the client just needs to discard the token.
        # But we can also call sign_out on the backend if we had a session.
        # Here we just acknowledge.
        res = supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

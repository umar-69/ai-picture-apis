from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.dependencies import get_current_user, get_supabase_admin
from app.schemas import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
def get_user_profile(current_user = Depends(get_current_user)):
    # current_user is a Supabase User object
    # Pydantic will try to extract fields. 
    # The User object has id, email, created_at, etc.
    return current_user

@router.delete("/me")
def delete_user_account(
    current_user = Depends(get_current_user),
    supabase_admin: Client = Depends(get_supabase_admin)
):
    try:
        # Delete user using admin client
        # current_user.id is the UUID of the user
        supabase_admin.auth.admin.delete_user(current_user.id)
        return {"message": "Account deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

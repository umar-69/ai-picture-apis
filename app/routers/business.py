from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas import BusinessProfileCreate, BusinessProfileResponse
from app.dependencies import get_current_user, get_supabase
from supabase import Client

router = APIRouter(prefix="/business", tags=["Business Profile"])

@router.get("/", response_model=BusinessProfileResponse)
def get_business_profile(
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    try:
        res = supabase.table("business_profiles").select("*").eq("id", current_user.id).single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Business profile not found")
        return res.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/", response_model=BusinessProfileResponse)
def create_or_update_business_profile(
    profile: BusinessProfileCreate,
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    try:
        data = profile.dict(exclude_unset=True)
        data["id"] = current_user.id
        
        # Upsert (insert or update)
        res = supabase.table("business_profiles").upsert(data).execute()
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

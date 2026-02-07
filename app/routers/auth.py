from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas import UserSignup, UserLogin
from app.dependencies import get_supabase
from supabase import Client

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/signup")
def signup(user: UserSignup, supabase: Client = Depends(get_supabase)):
    try:
        # 1. Create the auth user
        res = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password,
            "options": {
                "data": user.metadata or {}
            }
        })

        # 2. If user was created, set up account records
        new_user = res.user if hasattr(res, 'user') else (res.get('user') if isinstance(res, dict) else None)
        if new_user:
            user_id = str(new_user.id) if hasattr(new_user, 'id') else str(new_user.get('id', ''))
            if user_id:
                metadata = user.metadata or {}
                _setup_new_account(supabase, user_id, metadata)

        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _setup_new_account(supabase: Client, user_id: str, metadata: dict):
    """Create user_profiles, credit_balances, and Free subscription for a new user."""
    try:
        # Create user profile with metadata if provided
        profile_data = {
            "id": user_id,
            "first_name": metadata.get("first_name", metadata.get("full_name", "").split(" ")[0] if metadata.get("full_name") else None),
            "last_name": metadata.get("last_name", " ".join(metadata.get("full_name", "").split(" ")[1:]) if metadata.get("full_name") else None),
            "creative_type": metadata.get("creative_type"),
            "use_case": metadata.get("use_case"),
        }
        # Remove None values
        profile_data = {k: v for k, v in profile_data.items() if v is not None}
        profile_data["id"] = user_id  # always include id
        supabase.table("user_profiles").insert(profile_data).execute()

        # Look up the Free plan
        plans_res = supabase.table("plans").select("id, credit_limit").eq("name", "Free").execute()
        if plans_res.data:
            free_plan = plans_res.data[0]
            plan_id = free_plan["id"]
            credit_limit = free_plan["credit_limit"]

            # Create subscription (Free plan)
            supabase.table("subscriptions").insert({
                "user_id": user_id,
                "plan_id": plan_id,
                "status": "active"
            }).execute()

            # Create credit balance
            supabase.table("credit_balances").insert({
                "user_id": user_id,
                "total_credits": credit_limit,
                "used_credits": 0,
                "remaining_credits": credit_limit
            }).execute()

            # Log the initial credit grant
            supabase.table("credit_transactions").insert({
                "user_id": user_id,
                "amount": credit_limit,
                "type": "subscription_reset",
                "description": f"Initial {credit_limit} credits from Free plan"
            }).execute()
    except Exception:
        # Don't fail signup if account setup has issues — user can still log in
        pass

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

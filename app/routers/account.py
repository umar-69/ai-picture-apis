from fastapi import APIRouter, Depends, HTTPException, status, Query
from supabase import Client
from app.dependencies import get_current_user, get_supabase
from app.schemas import (
    UserProfileUpdate, UserProfileResponse,
    SubscriptionResponse, PlanResponse,
    CreditBalanceResponse, CreditTransactionResponse,
    UsageLogResponse, AccountSummaryResponse
)

router = APIRouter(prefix="/account", tags=["Account"])


# ─── Profile ─────────────────────────────────────────────────────

@router.get("/profile", response_model=UserProfileResponse)
def get_profile(
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Get the current user's profile (first name, last name, creative type, etc.)."""
    try:
        res = supabase.table("user_profiles").select("*").eq("id", str(current_user.id)).execute()
        if not res.data:
            # Profile doesn't exist yet — return empty shell
            return UserProfileResponse(id=str(current_user.id))
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/profile", response_model=UserProfileResponse)
def update_profile(
    profile: UserProfileUpdate,
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Create or update the current user's profile."""
    try:
        data = profile.dict(exclude_unset=True)
        data["id"] = str(current_user.id)
        res = supabase.table("user_profiles").upsert(data).execute()
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Subscription ────────────────────────────────────────────────

@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Get the current user's subscription with plan details."""
    try:
        res = supabase.table("subscriptions") \
            .select("*, plans(*)") \
            .eq("user_id", str(current_user.id)) \
            .execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="No subscription found")
        row = res.data[0]
        # Flatten the joined plan data
        plan_data = row.pop("plans", None)
        row["plan"] = plan_data
        return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Credits ─────────────────────────────────────────────────────

@router.get("/credits", response_model=CreditBalanceResponse)
def get_credits(
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Get the current user's credit balance (total, used, remaining)."""
    try:
        res = supabase.table("credit_balances") \
            .select("*") \
            .eq("user_id", str(current_user.id)) \
            .execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="No credit balance found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/credits/history", response_model=list[CreditTransactionResponse])
def get_credit_history(
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Get paginated credit transaction history."""
    try:
        res = supabase.table("credit_transactions") \
            .select("*") \
            .eq("user_id", str(current_user.id)) \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Usage ───────────────────────────────────────────────────────

@router.get("/usage", response_model=list[UsageLogResponse])
def get_usage(
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Get paginated usage logs showing every action and its credit cost."""
    try:
        res = supabase.table("usage_logs") \
            .select("*") \
            .eq("user_id", str(current_user.id)) \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Summary (Dashboard overview) ───────────────────────────────

@router.get("/summary", response_model=AccountSummaryResponse)
def get_account_summary(
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Combined account overview for the dashboard.
    Returns profile, subscription with plan, credit balance, and recent usage.
    """
    user_id = str(current_user.id)
    try:
        # Profile
        profile_res = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        profile = profile_res.data[0] if profile_res.data else {"id": user_id}

        # Subscription + plan
        sub_res = supabase.table("subscriptions") \
            .select("*, plans(*)") \
            .eq("user_id", user_id) \
            .execute()
        subscription = None
        if sub_res.data:
            row = sub_res.data[0]
            plan_data = row.pop("plans", None)
            row["plan"] = plan_data
            subscription = row

        # Credit balance
        credit_res = supabase.table("credit_balances").select("*").eq("user_id", user_id).execute()
        credits = credit_res.data[0] if credit_res.data else None

        # Recent usage (last 10)
        usage_res = supabase.table("usage_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()
        recent_usage = usage_res.data

        return AccountSummaryResponse(
            profile=profile,
            subscription=subscription,
            credits=credits,
            recent_usage=recent_usage
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Plans (public, no auth needed) ─────────────────────────────

@router.get("/plans", response_model=list[PlanResponse])
def list_plans(supabase: Client = Depends(get_supabase)):
    """List all available plans. Public endpoint."""
    try:
        res = supabase.table("plans").select("*").order("price_monthly").execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

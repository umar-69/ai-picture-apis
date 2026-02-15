from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.dependencies import get_current_user, get_supabase
from app.schemas import (
    EnvironmentCreate, EnvironmentUpdate, EnvironmentResponse,
    FolderCreate, FolderUpdate, FolderResponse
)

router = APIRouter(tags=["Environments"])


def _normalize_entity_name(name: str) -> str:
    """Normalize names so matching is consistent across API/UI input."""
    return " ".join((name or "").strip().split())


def _assert_unique_environment_name(
    supabase: Client,
    user_id: str,
    name: str,
    exclude_id: str | None = None,
) -> None:
    target = _normalize_entity_name(name).lower()
    rows = (
        supabase.table("environments")
        .select("id, name")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    for row in rows:
        if exclude_id and row.get("id") == exclude_id:
            continue
        if _normalize_entity_name(row.get("name", "")).lower() == target:
            raise HTTPException(status_code=409, detail="Environment name already exists")


def _assert_unique_folder_name(
    supabase: Client,
    user_id: str,
    environment_id: str,
    name: str,
    exclude_id: str | None = None,
) -> None:
    target = _normalize_entity_name(name).lower()
    rows = (
        supabase.table("datasets")
        .select("id, name")
        .eq("user_id", user_id)
        .eq("environment_id", environment_id)
        .execute()
        .data
        or []
    )
    for row in rows:
        if exclude_id and row.get("id") == exclude_id:
            continue
        if _normalize_entity_name(row.get("name", "")).lower() == target:
            raise HTTPException(status_code=409, detail="Folder name already exists in this environment")


# ─── Environments CRUD ───────────────────────────────────────────

@router.get("/environments", response_model=dict)
def list_environments(
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """List all environments belonging to the authenticated user."""
    try:
        res = supabase.table("environments") \
            .select("*") \
            .eq("user_id", str(current_user.id)) \
            .order("created_at") \
            .execute()
        return {"environments": res.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/environments", response_model=EnvironmentResponse, status_code=201)
def create_environment(
    body: EnvironmentCreate,
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Create a new environment."""
    try:
        clean_name = _normalize_entity_name(body.name)
        if not clean_name:
            raise HTTPException(status_code=400, detail="Environment name is required")

        _assert_unique_environment_name(supabase, str(current_user.id), clean_name)

        res = supabase.table("environments").insert({
            "name": clean_name,
            "user_id": str(current_user.id)
        }).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create environment")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/environments/{environment_id}", response_model=EnvironmentResponse)
def update_environment(
    environment_id: str,
    body: EnvironmentUpdate,
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Rename an environment. Must belong to the authenticated user."""
    try:
        clean_name = _normalize_entity_name(body.name)
        if not clean_name:
            raise HTTPException(status_code=400, detail="Environment name is required")

        _assert_unique_environment_name(
            supabase,
            str(current_user.id),
            clean_name,
            exclude_id=environment_id,
        )

        res = supabase.table("environments") \
            .update({"name": clean_name}) \
            .eq("id", environment_id) \
            .eq("user_id", str(current_user.id)) \
            .execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Environment not found or not owned by you")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/environments/{environment_id}")
def delete_environment(
    environment_id: str,
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Delete an environment and all its folders/datasets (cascade).
    The FK cascade on datasets.environment_id automatically deletes all
    folders inside this environment, which in turn cascade-deletes their images.
    """
    try:
        # Verify ownership before deleting
        check = supabase.table("environments") \
            .select("id") \
            .eq("id", environment_id) \
            .eq("user_id", str(current_user.id)) \
            .execute()
        if not check.data:
            raise HTTPException(status_code=404, detail="Environment not found or not owned by you")

        supabase.table("environments") \
            .delete() \
            .eq("id", environment_id) \
            .eq("user_id", str(current_user.id)) \
            .execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Folders (Datasets within Environments) ──────────────────────

@router.get("/environments/{environment_id}/folders", response_model=dict)
def list_folders(
    environment_id: str,
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """List all folders (datasets) within a specific environment."""
    try:
        # Verify the environment belongs to this user
        env_check = supabase.table("environments") \
            .select("id") \
            .eq("id", environment_id) \
            .eq("user_id", str(current_user.id)) \
            .execute()
        if not env_check.data:
            raise HTTPException(status_code=404, detail="Environment not found or not owned by you")

        res = supabase.table("datasets") \
            .select("*") \
            .eq("environment_id", environment_id) \
            .eq("user_id", str(current_user.id)) \
            .order("created_at") \
            .execute()
        return {"folders": res.data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/environments/{environment_id}/folders", response_model=FolderResponse, status_code=201)
def create_folder(
    environment_id: str,
    body: FolderCreate,
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Create a new folder (dataset) inside an environment."""
    try:
        clean_name = _normalize_entity_name(body.name)
        if not clean_name:
            raise HTTPException(status_code=400, detail="Folder name is required")

        # Verify the environment belongs to this user
        env_check = supabase.table("environments") \
            .select("id") \
            .eq("id", environment_id) \
            .eq("user_id", str(current_user.id)) \
            .execute()
        if not env_check.data:
            raise HTTPException(status_code=404, detail="Environment not found or not owned by you")

        _assert_unique_folder_name(
            supabase,
            str(current_user.id),
            environment_id,
            clean_name,
        )

        res = supabase.table("datasets").insert({
            "name": clean_name,
            "environment_id": environment_id,
            "user_id": str(current_user.id)
        }).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create folder")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/folders/{folder_id}", response_model=FolderResponse)
def update_folder(
    folder_id: str,
    body: FolderUpdate,
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Rename a folder. Must belong to the authenticated user."""
    try:
        clean_name = _normalize_entity_name(body.name)
        if not clean_name:
            raise HTTPException(status_code=400, detail="Folder name is required")

        folder_row = supabase.table("datasets") \
            .select("id, environment_id") \
            .eq("id", folder_id) \
            .eq("user_id", str(current_user.id)) \
            .execute()
        if not folder_row.data:
            raise HTTPException(status_code=404, detail="Folder not found or not owned by you")

        env_id = folder_row.data[0].get("environment_id")
        _assert_unique_folder_name(
            supabase,
            str(current_user.id),
            env_id,
            clean_name,
            exclude_id=folder_id,
        )

        res = supabase.table("datasets") \
            .update({"name": clean_name}) \
            .eq("id", folder_id) \
            .eq("user_id", str(current_user.id)) \
            .execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Folder not found or not owned by you")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/folders/{folder_id}")
def delete_folder(
    folder_id: str,
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Delete a folder and all its images (cascade).
    Also cleans up images from Supabase Storage.
    """
    try:
        # Verify ownership
        check = supabase.table("datasets") \
            .select("id") \
            .eq("id", folder_id) \
            .eq("user_id", str(current_user.id)) \
            .execute()
        if not check.data:
            raise HTTPException(status_code=404, detail="Folder not found or not owned by you")

        # Clean up storage files for this dataset
        try:
            images = supabase.table("dataset_images") \
                .select("image_url") \
                .eq("dataset_id", folder_id) \
                .execute()
            if images.data:
                # Extract storage paths from URLs and delete
                paths = []
                for img in images.data:
                    url = img.get("image_url", "")
                    # Extract path after /dataset-images/
                    if "/dataset-images/" in url:
                        path = url.split("/dataset-images/")[-1]
                        paths.append(path)
                if paths:
                    supabase.storage.from_("dataset-images").remove(paths)
        except Exception as storage_err:
            print(f"Warning: Storage cleanup failed: {storage_err}")
            # Continue with DB deletion even if storage cleanup fails

        # Delete from DB (cascade deletes dataset_images rows)
        supabase.table("datasets") \
            .delete() \
            .eq("id", folder_id) \
            .eq("user_id", str(current_user.id)) \
            .execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

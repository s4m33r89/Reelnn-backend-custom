from fastapi import APIRouter
from utils.db_utils.bundle_db import BundleDatabase

router = APIRouter()
bundle_db = BundleDatabase()

@router.get("/show/{sid}/bundles")
def get_show_bundles(sid: int):
    raw_bundles = bundle_db.get_bundles_for_show(sid)
    
    safe_bundles = []
    for b in raw_bundles:
        safe_bundles.append({
            "title": b.get("title"),
            "season": b.get("season"),
            "episode_range": b.get("episode_range"),
            "file_hash": b.get("file_hash"),
            "file_id": b.get("file_id"), # Kept for legacy support
            "size": b.get("size"),       # NEW: File size for UI
            "file_name": b.get("file_name"), # NEW: Filename
            "note": b.get("note")
        })

    return {
        "show_id": sid,
        "bundles": safe_bundles
    }

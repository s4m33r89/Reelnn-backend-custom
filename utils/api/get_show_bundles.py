from fastapi import APIRouter
from utils.db_utils.bundle_db import BundleDatabase

router = APIRouter()
bundle_db = BundleDatabase()

@router.get("/show/{sid}/bundles")
def get_show_bundles(sid: int):
    bundles = bundle_db.get_bundles_for_show(sid)
    return {
        "show_id": sid,
        "bundles": bundles
    }

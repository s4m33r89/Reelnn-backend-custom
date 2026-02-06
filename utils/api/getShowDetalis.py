from typing import Dict, Any, List
from utils.db_utils.show_db import ShowDatabase
from utils.db_utils.bundle_db import BundleDatabase


def get_show_details(sid: int) -> Dict[str, Any]:
    """
    Retrieve show details by show ID (sid), including bundled episodes if available.
    """
    try:
        sid = int(sid)
        
        db = ShowDatabase()
        show = db.find_show_by_id(sid)

        if not show:
            return {
                "status": "error",
                "message": f"Show with ID {sid} not found"
            }

        result: Dict[str, Any] = {}
        
        fields = [
            "title", "original_title", "release_date", "overview",
            "poster_path", "backdrop_path", "popularity", "vote_average",
            "vote_count", "genres", "logo", "cast", "creators", "links",
            "studios", "season", "total_episodes", "total_seasons",
            "status", "trailer"
        ]
        
        for field in fields:
            if field in show:
                result[field] = show[field]

        result["id"] = int(sid)
        result["sid"] = int(sid)

        if "season" in result and isinstance(result["season"], list):
            for season in result["season"]:
                if "episodes" in season and isinstance(season["episodes"], list):
                    season["episodes"].sort(key=lambda x: x.get("episode_number", 0))

        # --- Bundle Logic ---
        bundle_db = BundleDatabase()
        bundles = bundle_db.get_bundles_for_show(sid)
        
        result["bundles"] = []
        if bundles:
            for bundle in bundles:
                # Use HASH if available, otherwise fall back to ID
                identifier = str(bundle.get("file_hash") or bundle.get("file_id", ""))

                clean_bundle = {
                    "title": str(bundle.get("title", "")),
                    "season": int(bundle.get("season", 0)) if bundle.get("season") else None,
                    "episode_range": str(bundle.get("episode_range", "")) if bundle.get("episode_range") else None,
                    "file_id": identifier, 
                    "chat_id": int(bundle.get("chat_id", 0)) if bundle.get("chat_id") else None,
                    "msg_id": int(bundle.get("msg_id", 0)) if bundle.get("msg_id") else None,
                    "is_bundle": bool(bundle.get("is_bundle", True)),
                    "source": str(bundle.get("source", "telegram")),
                    "note": str(bundle.get("note", "")),
                    "show_id": int(bundle.get("show_id", 0)) if bundle.get("show_id") else None,
                }
                result["bundles"].append(clean_bundle)
        
        return result

    except Exception as e:
        import traceback
        print(f"[ERROR] get_show_details failed: {e}")
        print(traceback.format_exc())
        return {
            "status": "error", 
            "message": "Internal server error"
        }
from pymongo import MongoClient
from typing import List, Dict, Any, Optional, Union
import config

class BundleDatabase:
    def __init__(self):
        self.client = MongoClient(config.DATABASE_URL)
        self.db = self.client["reelnnback"]
        self.collection = self.db["bundles"]

        # Indexes
        self.collection.create_index("show_id")
        self.collection.create_index("title")
        self.collection.create_index("season")
        self.collection.create_index("file_id", unique=True)
        # Used for secure short links
        self.collection.create_index("file_hash") 

    def upsert_bundle(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update a bundle by file_id"""
        try:
            if data.get("show_id") is not None:
                data["show_id"] = int(data["show_id"])
                
            result = self.collection.update_one(
                {"file_id": data["file_id"]},
                {"$set": data},
                upsert=True
            )
            return {
                "status": "updated" if result.modified_count else "inserted",
                "matched": result.matched_count,
                "modified": result.modified_count
            }
        except Exception as e:
            print(f"[ERROR] upsert_bundle failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_bundles_for_show(self, show_id: Optional[Union[int, str]]) -> List[Dict[str, Any]]:
        """
        Get all bundles for a specific show_id.
        """
        try:
            if show_id is None:
                return []
            
            try:
                show_id_int = int(show_id)
                cursor = self.collection.find(
                    {"show_id": show_id_int, "is_bundle": True},
                    {"_id": 0}
                ).sort("season", 1)
                bundles = list(cursor)
            except ValueError:
                bundles = []

            if not bundles:
                show_id_str = str(show_id)
                cursor = self.collection.find(
                    {"show_id": show_id_str, "is_bundle": True},
                    {"_id": 0}
                ).sort("season", 1)
                bundles = list(cursor)
            
            return bundles
            
        except Exception as e:
            print(f"[ERROR] get_bundles_for_show failed: {e}")
            return []

    def get_bundle_by_hash_or_id(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Find a bundle by its file_hash (preferred) or file_id.
        """
        # 1. Try Hash (Secure Short ID)
        bundle = self.collection.find_one({"file_hash": identifier})
        if bundle:
            return bundle
            
        # 2. Fallback to File ID
        return self.collection.find_one({"file_id": identifier})

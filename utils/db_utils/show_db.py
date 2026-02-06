from pymongo import MongoClient
from typing import Dict, List, Any, Optional
from utils.db_utils.mongo_client import get_database

class ShowDatabase:
    def __init__(self):
        """Initialize MongoDB connection."""
        db = get_database("reelnnback")
        self.shows_collection = db["shows"]
        
        self.shows_collection.create_index("sid", unique=True)
    
    def upsert_show(self, show_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store or update show data in MongoDB, handling complex nested structures.
        
        Args:
            show_dict: Dictionary containing show data
            
        Returns:
            Dict with operation status and show
        """
        show_id = show_dict.get("sid")
        
        if not show_id:
            return {"status": "error", "message": "Show ID (sid) is required"}
        
        try:
            existing_show = self.shows_collection.find_one({"sid": show_id})
            
            if existing_show:
                fields_to_update = [
                    "title", "original_title", "release_date", "overview", 
                    "poster_path", "backdrop_path", "popularity", 
                    "vote_average", "vote_count", "genres", "logo", "cast", 
                    "creators", "links", "studios", "file_hash", "msg_id", 
                    "chat_id", "total_seasons", "total_episodes", "status", "trailer"
                ]
                
                update_doc = {}
                for field in fields_to_update:
                    if field in show_dict:
                        update_doc[field] = show_dict[field]
                
                if "season" in show_dict:
                    if "season" not in existing_show:
                        existing_show["season"] = []
                    
                    for new_season in show_dict.get("season", []):
                        season_number = new_season["season_number"]
                        
                        existing_season = None
                        for s in existing_show["season"]:
                            if s["season_number"] == season_number:
                                existing_season = s
                                break
                        
                        if existing_season:
                            if "episodes" not in existing_season:
                                existing_season["episodes"] = []
                            
                            for new_episode in new_season.get("episodes", []):
                                episode_number = new_episode["episode_number"]
                                
                                existing_episode = None
                                for e in existing_season["episodes"]:
                                    if e["episode_number"] == episode_number:
                                        existing_episode = e
                                        break
                                
                                if existing_episode:
                                    if "quality" not in existing_episode:
                                        existing_episode["quality"] = []
                                    
                                    # Append all new quality entries without checking for duplicates
                                    existing_episode["quality"].extend(new_episode.get("quality", []))
                                else:
                                    existing_season["episodes"].append(new_episode)
                        else:
                            existing_show["season"].append(new_season)
                    
                    update_doc["season"] = existing_show["season"]
                
                result = self.shows_collection.update_one(
                    {"sid": show_id},
                    {"$set": update_doc}
                )
                
                return {
                    "status": "updated",
                    "sid": show_id,
                    "modified_count": result.modified_count
                }
            else:
                result = self.shows_collection.insert_one(show_dict)
                
                return {
                    "status": "inserted",
                    "sid": show_id,
                    "inserted_id": str(result.inserted_id)
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def find_show_by_id(self, show_id: int) -> Optional[Dict[str, Any]]:
        """Find a show by its ID."""
        try:
            show_id = int(show_id)
            show = self.shows_collection.find_one({"sid": show_id})
            print(f"Searching for show with sid: {show_id}, Found: {show is not None}")
            return show
        except Exception as e:
            print(f"Error finding show: {str(e)}")
            return None
    
    def find_shows_by_title(self, title_query: str) -> List[Dict[str, Any]]:
        """Find shows by title (standard VPS-compatible regex search)."""
        try:
            cursor = self.shows_collection.find(
                {"title": {"$regex": title_query, "$options": "i"}}
            ).limit(20)
            return list(cursor)
        except Exception as e:
            print(f"Error searching shows: {str(e)}")
            return []

    
    def delete_show(self, show_id: int) -> Dict[str, Any]:
        """Delete a show by its ID."""
        try:
            result = self.shows_collection.delete_one({"sid": show_id})
            if result.deleted_count > 0:
                return {
                    "status": "success",
                    "message": f"Show with ID {show_id} deleted",
                    "deleted_count": result.deleted_count
                }
            else:
                return {
                    "status": "not_found",
                    "message": f"Show with ID {show_id} not found"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def find_shows_paginated(self, skip: int, limit: int, sort_fields=None) -> tuple:
        """
        Find shows with pagination and sorting.
        
        Args:
            skip: Number of documents to skip
            limit: Number of documents to return
            sort_fields: List of tuples with field name and direction (1 for ascending, -1 for descending)
            
        Returns:
            Tuple of (list of shows, total count)
        """
        if sort_fields is None:
            sort_fields = [("_id", -1)]  # Default sort by newest first
            
        total_count = self.shows_collection.count_documents({})
        projection = {
            "_id": 0,
            "sid": 1,
            "title": 1,
            "release_date": 1,
            "poster_path": 1,
            "vote_average": 1,
            "vote_count": 1
        }
        
        cursor = self.shows_collection.find({}, projection) \
            .sort(sort_fields) \
            .skip(skip) \
            .limit(limit)
        paginated_entries = []
        for entry in cursor:
            year = None
            if "release_date" in entry and entry["release_date"]:
                try:
                    year = int(entry["release_date"].split("-")[0])
                except (IndexError, ValueError, AttributeError):
                    pass
            
            processed_entry = {
                "id": entry.get("sid"),
                "title": entry.get("title"),
                "year": year,
                "poster": entry.get("poster_path"),
                "vote_average": entry.get("vote_average"),
                "vote_count": entry.get("vote_count"),
                "media_type": "show"
            }
            paginated_entries.append(processed_entry)
        
        return paginated_entries, total_count

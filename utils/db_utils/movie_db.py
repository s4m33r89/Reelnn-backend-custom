from pymongo import MongoClient
from typing import Dict, List, Any, Optional
from utils.db_utils.mongo_client import get_database


class MovieDatabase:
    def __init__(self):
        """Initialize MongoDB connection."""
        db = get_database("reelnnback")
        self.movies_collection = db["movies"]
        
        self.movies_collection.create_index("mid", unique=True)
    
    def upsert_movie(self, movie_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store or update movie data in MongoDB, handling quality variants.
        
        Args:
            movie_dict: Dictionary containing movie data
            
        Returns:
            Dict with operation status and movie ID
        """
        movie_id = movie_dict.get("mid")
        
        if not movie_id:
            return {"status": "error", "message": "Movie ID (mid) is required"}
        
        try:
            existing_movie = self.movies_collection.find_one({"mid": movie_id})
            
            if existing_movie:
                fields_to_update = [
                    "title", "original_title", "release_date", "overview", 
                    "poster_path", "backdrop_path", "popularity", 
                    "vote_average", "vote_count", "genres", "logo", 
                    "cast", "runtime", "directors", "links", "studios", 
                    "file_hash", "msg_id", "chat_id", "trailer"
                ]
                
                update_doc = {}
                for field in fields_to_update:
                    if field in movie_dict:
                        update_doc[field] = movie_dict[field]
                
                if "quality" in movie_dict:
                    if "quality" not in existing_movie:
                        existing_movie["quality"] = []
                    
                    # Append all new quality entries without checking for duplicates
                    existing_movie["quality"].extend(movie_dict.get("quality", []))
                    
                    update_doc["quality"] = existing_movie["quality"]
                
                result = self.movies_collection.update_one(
                    {"mid": movie_id},
                    {"$set": update_doc}
                )
                
                return {
                    "status": "updated",
                    "mid": movie_id,
                    "modified_count": result.modified_count
                }
            else:
                result = self.movies_collection.insert_one(movie_dict)
                
                return {
                    "status": "inserted",
                    "mid": movie_id,
                    "inserted_id": str(result.inserted_id)
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def find_movie_by_id(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """Find a movie by its ID."""
        try:
            movie_id = int(movie_id)
            movie = self.movies_collection.find_one({"mid": movie_id})
            print(f"Searching for movie with mid: {movie_id}, Found: {movie is not None}")
            return movie
        except Exception as e:
            print(f"Error finding movie: {str(e)}")
            return None
    
    def find_movies_by_title(self, title_query: str) -> List[Dict[str, Any]]:
        """Find movies by title (standard VPS-compatible regex search)."""
        try:
            # "i" option makes the search case-insensitive
            cursor = self.movies_collection.find(
                {"title": {"$regex": title_query, "$options": "i"}}
            ).limit(20)
            return list(cursor)
        except Exception as e:
            print(f"Error searching movies: {str(e)}")
            return []

    
    def delete_movie(self, movie_id: int) -> Dict[str, Any]:
        """Delete a movie by its ID."""
        try:
            result = self.movies_collection.delete_one({"mid": movie_id})
            if result.deleted_count > 0:
                return {
                    "status": "success",
                    "message": f"Movie with ID {movie_id} deleted",
                    "deleted_count": result.deleted_count
                }
            else:
                return {
                    "status": "not_found",
                    "message": f"Movie with ID {movie_id} not found"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
        
    def find_movies_paginated(self, skip: int, limit: int, sort_fields=None) -> tuple:
        """
        Find movies with pagination and sorting.
        
        Args:
            skip: Number of documents to skip
            limit: Number of documents to return
            sort_fields: List of tuples with field name and direction (1 for ascending, -1 for descending)
            
        Returns:
            Tuple of (list of movies, total count)
        """
        if sort_fields is None:
            sort_fields = [("_id", -1)]  # Default sort by newest first
            
        total_count = self.movies_collection.count_documents({})

        projection = {
            "_id": 0,
            "mid": 1,
            "title": 1,
            "release_date": 1,
            "poster_path": 1,
            "vote_average": 1,
            "vote_count": 1
        }
        
        cursor = self.movies_collection.find({}, projection) \
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
                "id": entry.get("mid"),
                "title": entry.get("title"),
                "year": year,
                "poster": entry.get("poster_path"),
                "vote_average": entry.get("vote_average"),
                "vote_count": entry.get("vote_count"),
                "media_type": "movie"
            }
            paginated_entries.append(processed_entry)
        
        return paginated_entries, total_count

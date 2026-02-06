from typing import List, Dict, Any
from utils.db_utils.movie_db import MovieDatabase
from utils.db_utils.show_db import ShowDatabase

def get_similar_by_genre(media_type: str, genres: List[str], limit: int = 20) -> List[Dict[str, Any]]:
    """
    Find movies or shows that match specific genres.
    
    Args:
        media_type: "movie" or "show"
        genres: List of genre names to search for (case-insensitive)
        limit: Maximum number of results to return
        
    Returns:
        List of media items matching at least one of the requested genres
    """
    if media_type == "movie":
        db = MovieDatabase()
        collection = db.movies_collection
        id_field = "mid"
    else:
        db = ShowDatabase()
        collection = db.shows_collection
        id_field = "sid"
    
    
    genre_queries = []
    for genre in genres:
        genre_queries.append({"genres": {"$regex": genre, "$options": "i"}})
    
    
    query = {"$or": genre_queries}
    
    
    results = list(collection.find(query).sort("popularity", -1).limit(limit))
    
    
    processed_results = []
    for item in results:
        
        year = None
        if "release_date" in item and item["release_date"]:
            try:
                year = int(item["release_date"].split("-")[0])
            except (IndexError, ValueError, AttributeError):
                pass
            
        processed_results.append({
            "id": item.get(id_field),
            "title": item.get("title"),
            "year": year,
            "poster": item.get("poster_path"),
            "vote_average": item.get("vote_average", 0),
            "media_type": media_type
        })
    

    return processed_results
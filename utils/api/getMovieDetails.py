from typing import Dict, Any
from utils.db_utils.movie_db import MovieDatabase

def get_movie_details(mid: int) -> Dict[str, Any]:
    """
    Retrieve movie details by movie ID (mid).
    
    Args:
        mid: The movie ID to look up
        
    Returns:
        Dictionary containing the requested movie fields or an error message
    """
    try:
        
        db = MovieDatabase()
        
        
        movie = db.find_movie_by_id(mid)
        
        if not movie:
            return {
                "status": "error",
                "message": f"Movie with ID {mid} not found"
            }
        
        
        result = {
            field: movie.get(field) for field in [
                "title", "release_date", "overview", "poster_path", 
                "backdrop_path", "popularity", "vote_average", 
                "genres", "logo", "quality", "cast", "runtime", "directors", "links", "studios", "trailer"
            ] if field in movie
        }
        result["id"] = mid
        

        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
from utils.cache_manager import get_trending
from typing import Dict, List, Any, Optional

def get_trending_entries(payload: Optional[Dict[str, List[int]]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get details for trending movies and shows.
    
    Args:
        payload: Optional dictionary with 'movie' and 'show' lists of IDs
                If not provided, will fetch from cache
    
    Returns:
        Dictionary with 'movie' and 'show' keys containing formatted entry details
    """
    
    
    if payload is None:
        
        return get_trending()
    else:
        
        
        from utils.db_utils.movie_db import MovieDatabase
        from utils.db_utils.show_db import ShowDatabase
        
        
        movie_ids = payload.get("movie", [])
        movie_db = MovieDatabase()
        movies = []
        for mid in movie_ids:
            movie = movie_db.find_movie_by_id(mid)
            if movie:
                processed_movie = {
                    "mid": movie.get("mid"),
                    "title": movie.get("title"),
                    "poster_path": movie.get("poster_path"),
                    "vote_average": movie.get("vote_average"),
                    "release_date": movie.get("release_date"),
                }
                movies.append(processed_movie)
        
        
        show_ids = payload.get("show", [])
        show_db = ShowDatabase()
        shows = []
        for sid in show_ids:
            show = show_db.find_show_by_id(sid)
            if show:
                processed_show = {
                    "sid": show.get("sid"),
                    "title": show.get("title"),
                    "poster_path": show.get("poster_path"),
                    "vote_average": show.get("vote_average"),
                    "release_date": show.get("release_date"),
                }
                shows.append(processed_show)
        
        return {
            "movie": movies,
            "show": shows
        }
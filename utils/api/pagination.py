from typing import Dict, Any, List
from utils.db_utils.movie_db import MovieDatabase
from utils.db_utils.show_db import ShowDatabase
import math

def get_paginated_entries(media_type: str, page: int = 1, items_per_page: int = 20, sort_by: str = "new_release") -> Dict[str, Any]:
    """
    Get paginated movie or show entries with sorting options.
    
    Args:
        media_type: "movie" or "show"
        page: Page number to retrieve
        items_per_page: Items per page
        sort_by: Sorting method (new_release, most_rated, release_date)
        
    Returns:
        Dict with items and pagination metadata
    """
    if media_type not in ["movie", "show"]:
        return {"status": "error", "message": "Media type must be 'movie' or 'show'"}
    
    try:
        
        if media_type == "movie":
            db = MovieDatabase()
        else:  
            db = ShowDatabase()
        
        
        sort_mapping = {
            "new": [("_id", -1)],  
            "most": [("vote_average", -1)],  
            "date": [("release_date", -1)]  
        }
        
        if sort_by not in sort_mapping:
            sort_by = "new"  
            
        sort_fields = sort_mapping[sort_by]
        
        
        skip = (page - 1) * items_per_page
        
        if media_type == "movie":
            items, total_count = db.find_movies_paginated(skip, items_per_page, sort_fields)
        else:
            items, total_count = db.find_shows_paginated(skip, items_per_page, sort_fields)
        
        
        total_pages = math.ceil(total_count / items_per_page)
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "items": items,
            "pagination": {
                "page": page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": items_per_page,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
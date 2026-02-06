from typing import List, Dict, Any, Union
from utils.cache_manager import get_latest

def get_latest_entries(media_type: str, limit: int = 8) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Get the most recently added movie or show entries from the database.
    
    Args:
        media_type: String specifying "movie" or "show"
        limit: Number of entries to return (default: 8)
        
    Returns:
        List of movie or show dictionaries or error dict with only specific fields
    """
    
    return get_latest(media_type, limit)
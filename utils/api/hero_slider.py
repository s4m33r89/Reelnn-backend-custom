from typing import Any, Dict, List
from utils.cache_manager import get_hero_slider

def get_hero_slider_items(limit: int = 3) -> List[Dict[str, Any]]:
    """
    Get the most recently added movies and shows for the hero slider.
    
    Args:
        limit: Total number of items to return
        
    Returns:
        List of the most recent movie and show items for the hero slider
    """
    
    return get_hero_slider()
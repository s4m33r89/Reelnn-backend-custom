from utils.db_utils.movie_db import MovieDatabase
from utils.db_utils.show_db import ShowDatabase
from fastapi import HTTPException
from typing import Dict, Any, Optional

async def get_video_details(
    content_id: str,
    media_type: str,
    quality_index: int = 0,
    season_number: Optional[int] = None,
    episode_number: Optional[int] = None
) -> Dict[str, Any]:
    """
    Retrieve video file details for streaming based on content type and quality preferences.
    """
    # Validation
    if media_type not in ["movie", "show"]:
        raise HTTPException(status_code=400, detail="Media type must be 'movie' or 'show'")

    # Convert ID safely
    try:
        c_id_int = int(content_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Content ID must be an integer")

    try:
        if media_type == "movie":
            return await _get_movie_file_details(c_id_int, quality_index)
        elif media_type == "show":
            if season_number is None or episode_number is None:
                raise HTTPException(status_code=400, detail="Season and episode numbers required for shows")
            return await _get_show_file_details(c_id_int, quality_index, season_number, episode_number)
            
    except HTTPException:
        raise # Re-raise known HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving video: {str(e)}")

async def _get_movie_file_details(movie_id: int, quality_index: int) -> Dict[str, Any]:
    db = MovieDatabase()
    movie = db.find_movie_by_id(movie_id)
    
    if not movie:
        raise HTTPException(status_code=404, detail=f"Movie with ID {movie_id} not found")
    
    if "quality" not in movie or not movie["quality"]:
        raise HTTPException(status_code=404, detail=f"No quality options available for movie {movie_id}")
    
    if quality_index < 0 or quality_index >= len(movie["quality"]):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid quality index. Available range: 0-{len(movie['quality'])-1}"
        )
    
    selected_quality = movie["quality"][quality_index]
    file_hash = selected_quality.get("file_hash")
    
    if not file_hash:
        raise HTTPException(status_code=404, detail="File Hash not found for selected quality")
    
    msg_id = selected_quality.get("msg_id")
    chat_id = selected_quality.get("chat_id")
    
    return {
        "msg_id": msg_id,
        "chat_id": chat_id,
        "hash": file_hash
    }

async def _get_show_file_details(
    show_id: int, 
    quality_index: int, 
    season_number: int, 
    episode_number: int
) -> Dict[str, Any]:
    db = ShowDatabase()
    show = db.find_show_by_id(show_id)
    
    if not show:
        raise HTTPException(status_code=404, detail=f"Show with ID {show_id} not found")
    
    season = next((s for s in show.get("season", []) if s["season_number"] == season_number), None)
    if not season:
        raise HTTPException(status_code=404, detail=f"Season {season_number} not found")
    
    episode = next((e for e in season.get("episodes", []) if e["episode_number"] == episode_number), None)
    if not episode:
        raise HTTPException(status_code=404, detail=f"Episode {episode_number} not found in season {season_number}")
    
    if "quality" not in episode or not episode["quality"]:
        raise HTTPException(status_code=404, detail=f"No quality options available for episode")
    
    if quality_index < 0 or quality_index >= len(episode["quality"]):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid quality index. Available range: 0-{len(episode['quality'])-1}"
        )
    
    selected_quality = episode["quality"][quality_index]
    file_hash = selected_quality.get("file_hash")
    
    if not file_hash:
        raise HTTPException(status_code=404, detail="File Hash not found for selected quality")
    
    msg_id = selected_quality.get("msg_id")
    chat_id = selected_quality.get("chat_id")
    
    if not msg_id or not chat_id:
        raise HTTPException(status_code=404, detail="File metadata incomplete")

    return {
        "msg_id": msg_id,
        "chat_id": chat_id,
        "hash": file_hash
    }

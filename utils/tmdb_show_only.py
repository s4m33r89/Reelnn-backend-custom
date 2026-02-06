# utils/tmdb_show_only.py (or inside same file if you prefer)

from utils.tmdb import fetch_tv_tmdb_data

async def fetch_tv_show_only_tmdb(title: str):
    """
    Fetch TMDB show-level data only (no season / episode).
    """
    # IMPORTANT: fetch_tv_tmdb_data must support this OR
    # you must have a separate TMDB function for show search
    return await fetch_tv_tmdb_data(title=title, season=0, episode=0, show_only=True)
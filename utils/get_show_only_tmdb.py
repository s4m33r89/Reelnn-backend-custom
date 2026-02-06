# utils/get_show_only_tmdb.py

from utils.tmdb import tmdb
from app import LOGGER

async def fetch_tv_show_only_tmdb(title: str):
    """
    Fetch SHOW-LEVEL TMDB data only (NO seasons, NO episodes).
    Safe for bundles.
    """
    if not title or not title.strip():
        LOGGER.warning("Empty title provided to fetch_tv_show_only_tmdb")
        return {"success": False, "error": "Empty title"}

    try:
        LOGGER.debug(f"TMDB search for: '{title}'")
        search = await tmdb.search().tv(query=title)

        if not search or not search.results:
            LOGGER.warning(f"No TMDB results for: '{title}'")
            return {"success": False, "error": "Show not found"}

        show = search.results[0]
        LOGGER.info(f"TMDB found: '{show.name}' (ID: {show.id})")

        return {
            "success": True,
            "data": {
                "tmdb_id": show.id,
                "title": show.name,
                "original_title": show.original_name,
                "poster_path": show.poster_path,
                "backdrop_path": show.backdrop_path,
                "overview": show.overview,
                "vote_average": show.vote_average,
                "vote_count": show.vote_count,
                "popularity": show.popularity,
                "first_air_date": show.first_air_date,
                # ⛔️ NO seasons here (by design)
            }
        }

    except Exception as e:
        LOGGER.error(f"Show-only TMDB error for '{title}': {e}")
        return {"success": False, "error": str(e)}

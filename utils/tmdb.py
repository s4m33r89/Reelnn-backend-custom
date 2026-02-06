import asyncio
import functools
from typing import Dict, Any, Optional, TypedDict
from themoviedb import aioTMDb
from app import LOGGER
from utils.utils import get_official_trailer_url
from config import TMDB_API_KEY

# Assuming normalize_show_tmdb exists in your utils/helpers
# from utils.normalizers import normalize_show_tmdb 

tmdb = aioTMDb(key=TMDB_API_KEY, language="en-US", region="US")

class TMDbResult(TypedDict):
    """Type definition for TMDb API results"""
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]

def async_lru_cache(maxsize=128, typed=False):
    def decorator(fn):
        _cache = {}
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key in _cache:
                return _cache[key]
            result = await fn(*args, **kwargs)
            if len(_cache) >= maxsize:
                _cache.pop(next(iter(_cache)))
            _cache[key] = result
            return result
        return wrapper
    return decorator

@async_lru_cache(maxsize=100)
async def fetch_movie_tmdb_data(title: str, year: Optional[int] = None) -> TMDbResult:
    """Fetch movie details from TMDb API"""
    try:
        try:
            search = await tmdb.search().movies(query=title, year=year)
            if not search or not hasattr(search, "results") or len(search.results) == 0:
                return {
                    "success": False,
                    "data": None,
                    "error": f"No movie found for '{title}'",
                }
            movie_id = search.results[0].id
        except Exception as e:
            LOGGER.error(f"Error searching for movie '{title}': {str(e)}")
            return {"success": False, "data": None, "error": f"Search error: {str(e)}"}

        movie_data = {
            "mid": movie_id,
            "title": "",
            "trailer": "",
            "original_title": "",
            "release_date": None,
            "overview": "",
            "poster_path": "",
            "directors": [],
            "backdrop_path": "",
            "runtime": 0,
            "popularity": 0,
            "vote_average": 0,
            "vote_count": 0,
            "cast": [],
            "logo": "",
            "genres": [],
            "studios": [],
            "links": [f"https://www.themoviedb.org/movie/{movie_id}"],
        }

        try:
            movie_details = await tmdb.movie(movie_id).details()
            movie_data["title"] = getattr(movie_details, "title", "")
            movie_data["original_title"] = getattr(movie_details, "original_title", "")
            movie_data["release_date"] = str(movie_details.release_date) if hasattr(movie_details, "release_date") and movie_details.release_date else None
            movie_data["overview"] = getattr(movie_details, "overview", "")
            movie_data["poster_path"] = getattr(movie_details, "poster_path", "") or ""
            movie_data["backdrop_path"] = getattr(movie_details, "backdrop_path", "") or ""
            movie_data["runtime"] = getattr(movie_details, "runtime", 0)
            movie_data["popularity"] = getattr(movie_details, "popularity", 0)
            movie_data["vote_average"] = getattr(movie_details, "vote_average", 0)
            movie_data["vote_count"] = getattr(movie_details, "vote_count", 0)
            
            companies = getattr(movie_details, "production_companies", [])
            movie_data["studios"] = [getattr(c, "name", "") for c in companies if hasattr(c, "name")]
        except Exception as e:
            LOGGER.warning(f"Error fetching movie details for '{title}': {str(e)}")

        try:
            logos = await tmdb.movie(movie_id).images()
            if hasattr(logos, "logos") and logos.logos:
                en_logos = [l for l in logos.logos if getattr(l, "iso_639_1", "") == "en"]
                in_logos = [l for l in logos.logos if getattr(l, "iso_639_1", "") == "in"]
                movie_data["logo"] = en_logos[0].file_path if en_logos else (in_logos[0].file_path if in_logos else "")
        except Exception as e:
            LOGGER.warning(f"Error fetching logos: {e}")

        try:
            ext = await tmdb.movie(movie_id).external_ids()
            if getattr(ext, "imdb_id", None):
                movie_data["links"].append(f"https://www.imdb.com/title/{ext.imdb_id}")
        except Exception: pass

        try:
            genre_data = await tmdb.genres().movie()
            genre_map = {g.id: g.name for g in genre_data.genres}
            g_ids = getattr(search.results[0], "genre_ids", [])
            movie_data["genres"] = [genre_map.get(gid) for gid in g_ids if gid in genre_map]
        except Exception: pass

        try:
            credits = await tmdb.movie(movie_id).credits()
            if hasattr(credits, "cast"):
                movie_data["cast"] = [{"name": getattr(a, "name", ""), "imageUrl": getattr(a, "profile_path", "") or "", "character": getattr(a, "character", "") or ""} for a in credits.cast[:20]]
            if hasattr(credits, "crew"):
                movie_data["directors"] = [getattr(m, "name", "") for m in credits.crew if getattr(m, "job", "") == "Director"]
        except Exception: pass

        await asyncio.sleep(1)
        try:
            videos = await tmdb.movie(movie_id).videos()
            movie_data["trailer"] = get_official_trailer_url(videos) or ""
        except Exception: pass

        return {"success": True, "data": movie_data, "error": None}
    except Exception as e:
        LOGGER.error(f"Critical error: {e}")
        return {"success": False, "data": None, "error": str(e)}

async def fetch_tv_show_tmdb_data(title: str) -> dict:
    """Fetch SHOW-LEVEL TMDB data only"""
    try:
        search = await tmdb.search().tv(query=title)
        if not search or not search.results:
            return {"success": False, "error": "Show not found"}
        
        show_id = search.results[0].id
        details = await tmdb.tv(show_id).details()
        
        data = {
            "sid": show_id,
            "title": getattr(details, "name", ""),
            "original_title": getattr(details, "original_name", ""),
            "overview": getattr(details, "overview", ""),
            "poster_path": getattr(details, "poster_path", ""),
            "backdrop_path": getattr(details, "backdrop_path", ""),
            "total_seasons": getattr(details, "number_of_seasons", 0),
            "total_episodes": getattr(details, "number_of_episodes", 0),
            "status": getattr(details, "status", ""),
            "genres": [getattr(g, "name", "") for g in getattr(details, "genres", [])],
            "studios": [getattr(c, "name", "") for c in getattr(details, "production_companies", [])],
        }
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def fetch_tv_tmdb_data(title: str, season: Optional[int] = None, episode: Optional[int] = None) -> TMDbResult:
    """Fetch TV show or Episode details from TMDb API"""
    try:
        tv_search = await tmdb.search().tv(query=title)
        if not tv_search or not tv_search.results:
            return {"success": False, "data": None, "error": f"No TV show found for '{title}'"}
        
        tv_show_id = tv_search.results[0].id

        # SHOW-LEVEL ONLY block
        if season is None or episode is None:
            show_details = await tmdb.tv(tv_show_id).details()
            # Note: Ensure normalize_show_tmdb is defined/imported
            return {"success": True, "data": locals().get('normalize_show_tmdb', lambda x: x)(show_details), "error": None}

        # EPISODE-LEVEL Logic
        tv_data = {
            "sid": tv_show_id,
            "title": "",
            "total_seasons": 0,
            "total_episodes": 0,
            "status": "",
            "trailer": "",
            "original_title": "",
            "release_date": None,
            "creators": [],
            "overview": "",
            "poster_path": "",
            "backdrop_path": "",
            "popularity": 0,
            "vote_average": 0,
            "vote_count": 0,
            "genres": [],
            "cast": [],
            "logo": "",
            "still_path": "",
            "studios": [],
            "links": [f"https://www.themoviedb.org/tv/{tv_show_id}"],
            "season": [{"season_number": int(season), "episodes": [{"episode_number": int(episode), "name": "", "runtime": 0, "overview": "", "still_path": "", "air_date": None}]}],
        }

        try:
            details = await tmdb.tv(tv_show_id).details()
            tv_data.update({
                "title": getattr(details, "name", ""),
                "total_seasons": len(getattr(details, "seasons", [])),
                "total_episodes": getattr(details, "number_of_episodes", 0),
                "status": getattr(details, "status", ""),
                "original_title": getattr(details, "original_name", ""),
                "overview": getattr(details, "overview", ""),
                "poster_path": getattr(details, "poster_path", ""),
                "backdrop_path": getattr(details, "backdrop_path", ""),
            })
        except Exception: pass

        try:
            ep = await tmdb.episode(tv_show_id, season, episode).details()
            target = tv_data["season"][0]["episodes"][0]
            target.update({
                "name": getattr(ep, "name", ""),
                "runtime": int(getattr(ep, "runtime", 0) or 0),
                "overview": getattr(ep, "overview", ""),
                "still_path": getattr(ep, "still_path", "") or "",
                "air_date": str(ep.air_date) if hasattr(ep, "air_date") and ep.air_date else None
            })
            tv_data["still_path"] = target["still_path"]
        except Exception as e:
            LOGGER.warning(f"Episode error: {e}")

        return {"success": True, "data": tv_data, "error": None}
    except Exception as e:
        LOGGER.error(f"TV API error: {e}")
        return {"success": False, "data": None, "error": str(e)}
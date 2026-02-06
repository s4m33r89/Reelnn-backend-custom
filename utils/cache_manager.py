import asyncio
import time
import logging
from .db_utils.movie_db import MovieDatabase
from .db_utils.show_db import ShowDatabase
from .db_utils.config_db import ConfigDatabase
from concurrent.futures import ThreadPoolExecutor
LOGGER = logging.getLogger(__name__)

thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cache_worker")


cache = {
    "hero_slider": [],
    "latest_movies": [],
    "latest_shows": [],
    "trending": {"movie": [], "show": []},
    "last_updated": 0    
}

def update_hero_slider_cache():
    """Update the hero slider cache with the most recent items"""
    try:
        movie_db = MovieDatabase()
        show_db = ShowDatabase()
        
        
        recent_movies = list(movie_db.movies_collection.find().sort("_id", -1).limit(3))
        
        
        recent_shows = list(show_db.shows_collection.find().sort("_id", -1).limit(3))
        
        
        slider_items = []
        
        
        for movie in recent_movies:
            item = {
                "id": movie.get("mid"),
                "title": movie.get("title"),
                "media_type": "movie",
                "backdrop_path": movie.get("backdrop_path"),
                "overview": movie.get("overview", ""),
                "release_date": movie.get("release_date", ""),
                "vote_average": movie.get("vote_average", 0),
                "genres": movie.get("genres", []),
                "logo": movie.get("logo", ""),
                "type": "movie",
                "_id_hex": str(movie.get("_id"))
            }
            slider_items.append(item)
        
        
        for show in recent_shows:
            item = {
                "id": show.get("sid"),
                "title": show.get("title", "Unknown Title"),
                "media_type": "show",
                "backdrop_path": show.get("backdrop_path"),
                "overview": show.get("overview", ""),
                "release_date": show.get("release_date", ""),
                "vote_average": show.get("vote_average", 0),
                "genres": show.get("genres", []),
                "type": "show",
                "logo": show.get("logo", ""),
                "_id_hex": str(show.get("_id"))
            }
            slider_items.append(item)
        
        
        slider_items.sort(key=lambda x: x["_id_hex"], reverse=True)
        
        
        for item in slider_items:
            item.pop("_id_hex", None)
        
        
        cache["hero_slider"] = slider_items
        
        
    except Exception as e:
        LOGGER.error(f"Error updating hero slider cache: {str(e)}")

def update_latest_entries_cache():
    """Update latest movies and shows cache"""
    try:
        movie_db = MovieDatabase()
        show_db = ShowDatabase()
        
        
        movie_projection = {
            "_id": 0, "mid": 1, "title": 1, "release_date": 1,
            "poster_path": 1, "vote_average": 1, "vote_count": 1
        }
        latest_movies = list(movie_db.movies_collection.find({}, movie_projection).sort("_id", -1).limit(21))
        
        processed_movies = []
        for movie in latest_movies:
            year = None
            if "release_date" in movie and movie["release_date"]:
                try:
                    year = int(movie["release_date"].split("-")[0])
                except (IndexError, ValueError, AttributeError):
                    pass
            
            processed_movie = {
                "id": movie.get("mid"),
                "title": movie.get("title"),
                "year": year,
                "poster": movie.get("poster_path"),
                "vote_average": movie.get("vote_average"),
                "vote_count": movie.get("vote_count"),
                "media_type": "movie"
            }
            processed_movies.append(processed_movie)
        
        cache["latest_movies"] = processed_movies
        
        
        show_projection = {
            "_id": 0, "sid": 1, "title": 1, "release_date": 1,
            "poster_path": 1, "vote_average": 1, "vote_count": 1
        }
        latest_shows = list(show_db.shows_collection.find({}, show_projection).sort("_id", -1).limit(21))
        
        processed_shows = []
        for show in latest_shows:
            year = None
            if "release_date" in show and show["release_date"]:
                try:
                    year = int(show["release_date"].split("-")[0])
                except (IndexError, ValueError, AttributeError):
                    pass
            
            processed_show = {
                "id": show.get("sid"),
                "title": show.get("title"),
                "year": year,
                "poster": show.get("poster_path"),
                "vote_average": show.get("vote_average"),
                "vote_count": show.get("vote_count"),
                "media_type": "show"
            }
            processed_shows.append(processed_show)
        
        cache["latest_shows"] = processed_shows
        
        
        
        
        
    except Exception as e:
        LOGGER.error(f"Error updating latest entries cache: {str(e)}")

def update_trending_cache():
    """Update trending movies and shows cache"""
    try:
        config_db = ConfigDatabase()
        movie_db = MovieDatabase()
        show_db = ShowDatabase()
        
        
        trending_config = config_db.get_trending_config()
        
        
        movie_ids = trending_config.get("movie", [])
        movies = []
        for mid in movie_ids:
            movie = movie_db.find_movie_by_id(mid)
            if movie:
                year = None
                if "release_date" in movie and movie["release_date"]:
                    try:
                        year = int(movie["release_date"].split("-")[0])
                    except (IndexError, ValueError, AttributeError):
                        pass
                processed_movie = {
                    "id": movie.get("mid"),
                    "title": movie.get("title"),
                    "poster": movie.get("poster_path"),
                    "vote_average": movie.get("vote_average"),
                    "year": year,
                }
                movies.append(processed_movie)
        
        
        show_ids = trending_config.get("show", [])
        shows = []
        for sid in show_ids:
            
            show = show_db.find_show_by_id(sid)
            if show:
                year = None
                if "release_date" in show and show["release_date"]:
                    try:
                        year = int(show["release_date"].split("-")[0])
                    except (IndexError, ValueError, AttributeError):
                        pass
                processed_show = {
                    "id": show.get("sid"),
                    "title": show.get("title"),
                    "poster": show.get("poster_path"),
                    "vote_average": show.get("vote_average"),
                    "year": year,
                }
                shows.append(processed_show)
        
        
        cache["trending"] = {
            "movie": movies,
            "show": shows
        }
        
        
        
        
        
    except Exception as e:
        LOGGER.error(f"Error updating trending cache: {str(e)}")


async def update_all_caches():
    """Update all caches with fresh data from MongoDB"""
    try:
        LOGGER.info("Starting cache update")
        
        
        await asyncio.gather(
            run_in_thread(update_hero_slider_cache),
            run_in_thread(update_latest_entries_cache),
            run_in_thread(update_trending_cache)
        )
        
        
        cache["last_updated"] = time.time()
        
        LOGGER.info("Cache update completed")
    except Exception as e:
        LOGGER.error(f"Error in cache update: {str(e)}")

async def run_in_thread(func):
    """Run a function in the thread pool"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(thread_pool, func)

async def start_cache_updater():
    """Start the background task that updates the cache every 3 minutes"""
    
    try:
        await update_all_caches()
    except Exception as e:
        LOGGER.error(f"Initial cache update failed: {str(e)}")
    
    
    while True:
        try:
            
            await asyncio.sleep(180)
            
            
            update_task = asyncio.create_task(update_all_caches())
            try:
                
                await asyncio.wait_for(update_task, timeout=60)
            except asyncio.TimeoutError:
                LOGGER.error("Cache update timed out after 60 seconds")
                
                
                
        except asyncio.CancelledError:
            
            LOGGER.info("Cache updater task cancelled")
            break
        except Exception as e:
            LOGGER.error(f"Error in cache updater: {str(e)}")
            
            await asyncio.sleep(10)



def get_hero_slider():
    """Get hero slider items from cache"""
    return cache["hero_slider"]

def get_latest(media_type: str, limit: int = 21):
    """Get latest entries from cache"""
    if media_type.lower() == "movie":
        return cache["latest_movies"][:limit]
    elif media_type.lower() == "show":
        return cache["latest_shows"][:limit]
    else:
        return {"status": "error", "message": "media_type must be 'movie' or 'show'"}

def get_trending():
    """Get trending entries from cache as a combined list with content type"""
    trending_data = cache["trending"]
    combined_list = []
    
    
    for movie in trending_data.get("movie", []):
        movie_with_type = movie.copy()
        movie_with_type["media_type"] = "movie"
        combined_list.append(movie_with_type)
    
    
    for show in trending_data.get("show", []):
        show_with_type = show.copy()
        show_with_type["media_type"] = "show"
        combined_list.append(show_with_type)
    
    return combined_list


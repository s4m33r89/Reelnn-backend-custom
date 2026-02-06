from typing import Dict, List, Any
import asyncio
import functools
import re

from utils.db_utils.movie_db import MovieDatabase
from utils.db_utils.show_db import ShowDatabase


# =====================================================
# ASYNC LRU CACHE (UNCHANGED FEATURE)
# =====================================================
def async_lru_cache(maxsize=100):
    """Async-compatible LRU cache decorator."""
    def decorator(fn):
        cache = {}
        cache_order = []

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            key = str((args, frozenset(kwargs.items())))

            if key in cache:
                cache_order.remove(key)
                cache_order.append(key)
                return cache[key]

            result = await fn(*args, **kwargs)
            cache[key] = result
            cache_order.append(key)

            if len(cache_order) > maxsize:
                oldest_key = cache_order.pop(0)
                cache.pop(oldest_key, None)

            return result

        def cache_info():
            return {"maxsize": maxsize, "currsize": len(cache)}

        def cache_clear():
            cache.clear()
            cache_order.clear()

        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return wrapper

    return decorator


# =====================================================
# PUBLIC CACHED SEARCH ENTRY
# =====================================================
@async_lru_cache(maxsize=100)
async def get_cached_search_results(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    return await search_all_media(query, limit)


# =====================================================
# SEARCH BOTH MEDIA TYPES CONCURRENTLY
# =====================================================
async def search_all_media(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    movie_task = asyncio.create_task(search_movies(query, limit // 2))
    show_task = asyncio.create_task(search_shows(query, limit // 2))

    movie_results, show_results = await asyncio.gather(movie_task, show_task)

    combined_results = movie_results + show_results

    # Final relevance sort
    combined_results.sort(
        key=lambda x: calculate_relevance_score(x, query),
        reverse=True
    )

    return combined_results


# =====================================================
# MOVIE SEARCH (VPS SAFE – REGEX)
# =====================================================
async def search_movies(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    movie_db = MovieDatabase()
    escaped_query = re.escape(query)

    cursor = movie_db.movies_collection.find(
        {"title": {"$regex": escaped_query, "$options": "i"}},
        {
            "_id": 0,
            "mid": 1,
            "title": 1,
            "poster_path": 1,
            "release_date": 1,
            "vote_average": 1,
            "vote_count": 1,
        }
    ).limit(limit)

    results = []
    for item in cursor:
        year = None
        if item.get("release_date"):
            try:
                year = int(item["release_date"].split("-")[0])
            except Exception:
                pass

        results.append({
            "id": item.get("mid"),
            "title": item.get("title"),
            "year": year,
            "poster": item.get("poster_path"),
            "vote_average": item.get("vote_average", 0),
            "vote_count": item.get("vote_count", 0),
            "media_type": "movie",
            "score": base_score(item, query),
        })

    return results


# =====================================================
# SHOW SEARCH (VPS SAFE – REGEX)
# =====================================================
async def search_shows(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    show_db = ShowDatabase()
    escaped_query = re.escape(query)

    cursor = show_db.shows_collection.find(
        {"title": {"$regex": escaped_query, "$options": "i"}},
        {
            "_id": 0,
            "sid": 1,
            "title": 1,
            "poster_path": 1,
            "release_date": 1,
            "vote_average": 1,
            "vote_count": 1,
        }
    ).limit(limit)

    results = []
    for item in cursor:
        year = None
        if item.get("release_date"):
            try:
                year = int(item["release_date"].split("-")[0])
            except Exception:
                pass

        results.append({
            "id": item.get("sid"),
            "title": item.get("title"),
            "year": year,
            "poster": item.get("poster_path"),
            "vote_average": item.get("vote_average", 0),
            "vote_count": item.get("vote_count", 0),
            "media_type": "show",
            "score": base_score(item, query),
        })

    return results


# =====================================================
# BASE SCORING (REPLACES ATLAS searchScore)
# =====================================================
def base_score(item: Dict[str, Any], query: str) -> float:
    score = 0.0
    title = item.get("title", "").lower()
    query_l = query.lower()

    if title == query_l:
        score += 100
    elif query_l in title:
        score += 50

    score += item.get("vote_average", 0) * 2
    score += min(item.get("vote_count", 0) / 100, 20)

    return score


# =====================================================
# FINAL RELEVANCE SCORE (UNCHANGED FEATURE)
# =====================================================
def calculate_relevance_score(item: Dict[str, Any], query: str) -> float:
    score = item.get("score", 0)

    vote_count = item.get("vote_count", 0)
    if vote_count > 1000:
        score *= 1.2
    elif vote_count > 500:
        score *= 1.1

    if item.get("title", "").lower() == query.lower():
        score *= 2

    return score
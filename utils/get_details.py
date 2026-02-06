import PTN
from typing import Dict, Any, Optional, TypedDict, Union, List

from utils.tmdb import (
    fetch_movie_tmdb_data,
    fetch_tv_tmdb_data,
    fetch_tv_show_tmdb_data,
)
from utils.mediainfo import media_quality
from utils.utils import get_readable_file_size
from utils.models.show_model import ShowSchema
from utils.models.movie_model import MovieSchema
from pyrogram.types import Message
from pyrogram import Client
from app import LOGGER


class ContentResult(TypedDict):
    success: bool
    data: Optional[Dict[str, Any]]
    _type: Optional[str]
    error: Optional[str]


# =========================
# MOVIE
# =========================
async def get_movie_details(
    title: str,
    client: Client,
    year: Optional[int],
    message: Message,
) -> ContentResult:
    try:
        tmdb = await fetch_movie_tmdb_data(title, year)
        if not tmdb.get("success"):
            return {"success": False, "error": tmdb.get("error"), "data": None, "_type": None}

        quality, media_info = await media_quality(client, message)
        quality = quality or "720p"

        file = message.video or message.document or message.animation
        data = tmdb["data"].copy()

        data["quality"] = [{
            "type": quality,
            "file_hash": file.file_unique_id[:6],
            "msg_id": message.id,
            "chat_id": message.chat.id,
            "size": get_readable_file_size(file.file_size),
            "audio": media_info.get("audio") or "N/A",
            "video_codec": media_info.get("video_codec") or "N/A",
            "file_type": media_info.get("file_type") or "N/A",
            "subtitle": media_info.get("subtitle") or "N/A",
        }]

        return {
            "success": True,
            "data": MovieSchema(**data).model_dump(),
            "_type": "movie",
            "error": None,
        }

    except Exception as e:
        LOGGER.error(f"Movie error: {e}")
        return {"success": False, "error": str(e), "data": None, "_type": None}


# =========================
# TV SINGLE EPISODE
# =========================
async def get_tv_details(
    title: str,
    client: Client,
    season: int,
    episode: int,
    message: Message,
) -> ContentResult:
    try:
        tmdb = await fetch_tv_tmdb_data(title, season, episode)
        if not tmdb.get("success"):
            return {"success": False, "error": tmdb.get("error"), "data": None, "_type": None}

        quality, media_info = await media_quality(client, message)
        quality = quality or "720p"

        file = message.video or message.document or message.animation
        data = tmdb["data"].copy()

        ep = data["season"][0]["episodes"][0]
        ep["quality"] = [{
            "type": quality,
            "file_hash": file.file_unique_id[:6],
            "msg_id": message.id,
            "chat_id": message.chat.id,
            "size": get_readable_file_size(file.file_size),
            "audio": media_info.get("audio") or "N/A",
            "video_codec": media_info.get("video_codec") or "N/A",
            "file_type": media_info.get("file_type") or "N/A",
            "subtitle": media_info.get("subtitle") or "N/A",
            "runtime": ep.get("runtime"),
        }]

        return {
            "success": True,
            "data": ShowSchema(**data).model_dump(),
            "_type": "show",
            "error": None,
        }

    except Exception as e:
        LOGGER.error(f"Episode error: {e}")
        return {"success": False, "error": str(e), "data": None, "_type": None}


# =========================
# TV SHOW ONLY (BUNDLES / SEASON)
# =========================
async def get_tv_show_only(title: str) -> ContentResult:
    try:
        tmdb = await fetch_tv_show_tmdb_data(title)
        if not tmdb.get("success"):
            return {"success": False, "error": tmdb.get("error"), "data": None, "_type": None}

        return {
            "success": True,
            "data": ShowSchema(**tmdb["data"]).model_dump(),
            "_type": "show",
            "error": None,
        }

    except Exception as e:
        LOGGER.error(f"Show-only error: {e}")
        return {"success": False, "error": str(e), "data": None, "_type": None}


# =========================
# ENTRY POINT
# =========================
async def get_content_details(
    mtitle: str,
    client: Client,
    message: Message,
) -> ContentResult:

    LOGGER.info(f"Processing content: {mtitle}")

    parsed = PTN.parse(mtitle)
    if not parsed.get("title"):
        return {"success": False, "error": "Parse failed", "data": None, "_type": None}

    title = " ".join(parsed["title"].replace("_", " ").replace("-", " ").split())
    year = parsed.get("year")
    season = parsed.get("season")
    episode: Union[int, List[int], None] = parsed.get("episode")

    LOGGER.info(
        f"Parsed: Title='{title}', Year={year}, Season={season}, Episode={episode}"
    )

    # MOVIE
    if season is None:
        return await get_movie_details(title, client, year, message)

    # BUNDLE OR SEASON-ONLY
    if episode is None or isinstance(episode, list):
        LOGGER.warning("Bundle/Season detected → fetching SHOW-level TMDB")
        return await get_tv_show_only(title)

    # SINGLE EPISODE
    return await get_tv_details(title, client, season, int(episode), message)
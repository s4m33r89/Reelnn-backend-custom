from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from asyncio import sleep, create_task, Queue

from app import LOGGER
import config
from utils.get_details import get_content_details
from utils.get_show_only_tmdb import fetch_tv_show_only_tmdb
from utils.db_utils.movie_db import MovieDatabase
from utils.db_utils.show_db import ShowDatabase
from utils.db_utils.bundle_db import BundleDatabase
from utils.utils import remove_redandent
from utils.auto_poster import auto_poster
from utils.cache_manager import update_all_caches
from utils.telegram_logger import send_info, send_error, send_warning
from utils.bundle_detector import is_bundle, extract_bundle_info

# ===============================
# CONFIG
# ===============================
WORKER_COUNT = 2
PROCESS_DELAY = 1
CACHE_DELAY = 30

# ===============================
# GLOBALS
# ===============================
message_queue: Queue = Queue()
worker_tasks = []
cache_update_scheduled = False

movie_db = MovieDatabase()
show_db = ShowDatabase()
bundle_db = BundleDatabase()

# ===============================
# HELPERS
# ===============================
def is_season_pack(title: str) -> bool:
    """Detect season packs like: S01.480p.WEB-DL..."""
    t = title.lower()
    return ".s01." in t and "e01" not in t and "episode" not in t

# ===============================
# WORKER STARTER (RESTORED)
# ===============================
async def start_workers(update_cache: bool = True):
    """
    Initialize worker tasks if they aren't running.
    Required by plugins/batch.py
    """
    global worker_tasks
    if worker_tasks:
        return
        
    LOGGER.info(f"Starting {WORKER_COUNT} video processing workers...")
    for i in range(WORKER_COUNT):
        task = create_task(process_video_queue(update_cache))
        worker_tasks.append(task)
        LOGGER.info("Started video worker #%d", i + 1)

# ===============================
# CORE PROCESSOR
# ===============================
async def process_video(client: Client, message: Message, update_cache: bool):
    global cache_update_scheduled
    try:
        file = message.video or message.document or message.animation
        if not file:
            return

        # -----------------------------
        # TITLE RESOLUTION
        # -----------------------------
        if config.USE_CAPTION:
            title = message.caption or message.text or ""
        else:
            title = file.file_name or file.file_id
        
        title = remove_redandent(title)

        # ===============================
        # BUNDLE / SEASON PACK HANDLING
        # ===============================
        if is_bundle(title) or is_season_pack(title):
            LOGGER.info(f"Processing Bundle: {title}")
            
            bundle_info = extract_bundle_info(title)
            show_id = None
            search_title = bundle_info.get("clean_title") or title

            try:
                LOGGER.info(f"Searching TMDB for bundle: '{search_title}'")
                tmdb = await fetch_tv_show_only_tmdb(search_title)
                
                if tmdb.get("success"):
                    show = tmdb["data"]
                    show_data = {
                        "sid": show["tmdb_id"],
                        "tmdb_id": show["tmdb_id"],
                        "title": show["title"],
                        "original_title": show.get("original_title"),
                        "poster_path": show.get("poster_path"),
                        "backdrop_path": show.get("backdrop_path"),
                        "overview": show.get("overview"),
                        "vote_average": show.get("vote_average"),
                        "vote_count": show.get("vote_count"),
                        "popularity": show.get("popularity"),
                        "release_date": show.get("first_air_date"),
                        "season": [],
                    }
                    # Upsert Show (Save if not exists)
                    if not show_db.find_show_by_id(show["tmdb_id"]):
                        show_db.insert_show(show_data)
                    else:
                        # Optional: Update existing show data if needed
                        show_db.upsert_show(show_data)
                        
                    show_id = show["tmdb_id"]
                    LOGGER.info(f"Bundle linked to show_id={show_id}")
                else:
                    LOGGER.warning(f"TMDB search failed for: '{search_title}'")
            except Exception as e:
                LOGGER.exception(f"Bundle TMDB resolution failed: {e}")

            # Generate File Hash
            file_unique_id = getattr(file, "file_unique_id", None)
            file_hash = file_unique_id[:6] if file_unique_id else None

            # Save Bundle
            bundle_db.upsert_bundle({
                "title": title,
                "show_id": show_id,
                "season": bundle_info.get("season"),
                "episode_range": bundle_info.get("episode_range") or "FULL SEASON",
                "file_id": file.file_id,
                "file_unique_id": file_unique_id, # Save unique ID
                "file_hash": file_hash,           # Save Hash
                "chat_id": message.chat.id,
                "msg_id": message.id,
                "is_bundle": True,
                "source": "telegram",
                "note": bundle_info.get("note", "Auto-detected")
            })

            status_msg = f"📦 Season / Bundle detected\nTitle: `{title}`\nSeason: {bundle_info.get('season')}"
            status_msg += f"\n✅ Linked to Show ID: {show_id}" if show_id else "\n⚠️ TMDB lookup failed (Saved without Show ID)"
            status_msg += f"\n🔑 Hash: `{file_hash}`"
            
            await send_warning(client, status_msg)
            return

        # ===============================
        # NORMAL METADATA FLOW (EXISTING)
        # ===============================
        # This logic handles standard movies and episodes using your original get_content_details
        result = await get_content_details(title, client, message)
        
        if not result or not result.get("success"):
            # Only warn if it really failed (sometimes get_content_details might return None if filtered)
            if result and not result.get("success"):
                await send_warning(client, f"Metadata failed:\n{title}")
            return

        media_details = result["data"]
        media_type = result["_type"]

        if media_type == "movie":
            res = movie_db.upsert_movie(media_details)
            await send_info(client, f"🎬 Movie {res['status']}: {media_details.get('title')}")
        elif media_type == "show":
            res = show_db.upsert_show(media_details)
            await send_info(client, f"📺 Show {res['status']}: {media_details.get('title')}")

        if config.POST_UPDATES:
            create_task(auto_poster(client, message, media_details, media_type))

        if update_cache and not cache_update_scheduled:
            cache_update_scheduled = True
            create_task(delayed_cache_update())

    except FloodWait as e:
        await sleep(e.value)
        await message_queue.put((client, message))
    except Exception as e:
        LOGGER.exception("Processing failed")
        await send_error(client, f"Processing failed: {str(e)}", e)

# ===============================
# WORKER LOOP
# ===============================
async def process_video_queue(update_cache: bool):
    while True:
        client, message = await message_queue.get()
        try:
            await process_video(client, message, update_cache)
            await sleep(PROCESS_DELAY)
        finally:
            message_queue.task_done()

# ===============================
# DELAYED CACHE UPDATE
# ===============================
async def delayed_cache_update():
    global cache_update_scheduled
    await sleep(CACHE_DELAY)
    await message_queue.join()
    LOGGER.info("Queue drained - running cache update")
    try:
        await update_all_caches()
    finally:
        cache_update_scheduled = False

# ===============================
# NEW UPLOAD HANDLER
# ===============================
@Client.on_message(filters.chat(config.AUTH_CHATS))
async def get_video(client: Client, message: Message):
    # Ensure workers are started
    await start_workers(update_cache=True)
    
    if message.video or message.document or message.animation:
        await message_queue.put((client, message))
        LOGGER.info("Queued new upload")
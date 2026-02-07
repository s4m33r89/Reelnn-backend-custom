from typing import List, Optional
from fastapi import FastAPI, Query, Request, HTTPException, Form, Depends
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyQuery
from fastapi.staticfiles import StaticFiles
import jwt
from datetime import datetime
from pathlib import Path
import math
import secrets
import mimetypes
import time
import asyncio
from contextlib import asynccontextmanager

from utils.db_utils.config_db import ConfigDatabase
from utils.db_utils.movie_db import MovieDatabase
from utils.db_utils.show_db import ShowDatabase
from utils.db_utils.bundle_db import BundleDatabase
from utils.api.search_results import get_cached_search_results
from utils.api.hero_slider import get_hero_slider_items
from utils.api.get_latest import get_latest_entries
from utils.api.getMovieDetails import get_movie_details
from utils.api.getShowDetalis import get_show_details
from utils.api.pagination import get_paginated_entries
from utils.api.get_trending import get_trending_entries
from utils.api.get_simillar import get_similar_by_genre
from utils.api.get_show_bundles import router as show_bundles_router
from utils.cache_manager import update_trending_cache
from utils.exceptions import InvalidHash
from utils.custom_dl import ByteStreamer
from web.auth import verify_token, authenticate_user
from state import work_loads, multi_clients
from app import LOGGER
from config import SITE_SECRET

app = FastAPI()
class_cache = {}
token_query = APIKeyQuery(name="token", auto_error=False)

BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)

templates_dir = BASE_DIR / "templates"
templates_dir.mkdir(exist_ok=True)

app.include_router(show_bundles_router, prefix="/api/v1")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Initialize DBs
movie_db = MovieDatabase()
show_db = ShowDatabase()
bundle_db = BundleDatabase()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    cache_cleaner_task = asyncio.create_task(periodic_cache_cleanup())
    yield
    cache_cleaner_task.cancel()
    try:
        await cache_cleaner_task
    except asyncio.CancelledError:
        pass

async def periodic_cache_cleanup():
    while True:
        await asyncio.sleep(900)  # 15 minutes
        clean_cache()
        LOGGER.debug(f"Cache cleaned. Items remaining: {len(class_cache)}")

def verify_stream_token(token: str):
    try:
        decoded = jwt.decode(token, SITE_SECRET, algorithms=["HS256"])
        if "expiry" in decoded and decoded["expiry"] < datetime.now().timestamp():
            raise HTTPException(status_code=401, detail="Token has expired")
        return decoded
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

# --- Auth Routes ---

@app.post("/api/v1/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """Login and get access token."""
    token = await authenticate_user(username, password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": token, "token_type": "bearer"}

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve the login page."""
    with open(templates_dir / "login.html") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/v1/auth-check")
async def auth_check(token_data: dict = Depends(verify_token)):
    """Check if the user is authenticated"""
    return {"authenticated": True, "user": token_data.get("sub", "Unknown")}

# --- Content Routes ---

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the admin interface"""
    with open(templates_dir / "index.html") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/v1/heroslider")
async def get_hero_slider(request: Request):
    items = get_hero_slider_items()
    return JSONResponse(content=items)

@app.get("/api/v1/getlatest/{media_type}")
async def get_latest(media_type: str, limit: int = Query(21, gt=0)):
    items = get_latest_entries(media_type, limit)
    return JSONResponse(content=items)

@app.get("/api/v1/getMovieDetails/{mid}")
async def getmovie_details(mid: str):
    details = get_movie_details(mid)
    if not details:
        raise HTTPException(status_code=404, detail="Movie not found")
    return JSONResponse(content=details)

@app.get("/api/v1/getShowDetails/{sid}")
async def getshow_details(sid: str):
    details = get_show_details(sid)
    if not details:
        raise HTTPException(status_code=404, detail="Show not found")
    return JSONResponse(content=details)

@app.get("/api/v1/paginated/{media_type}")
async def get_paginated(
    media_type: str,
    page: int = Query(1, gt=0),
    items_per_page: int = Query(20, gt=0, le=100),
    sort_by: str = Query("new", description="Sort by: new_release, most_rated, release_date"),
):
    response = get_paginated_entries(media_type, page, items_per_page, sort_by)
    if "status" in response and response["status"] == "error":
        raise HTTPException(status_code=400, detail=response["message"])
    return JSONResponse(content=response)

@app.get("/api/v1/trending")
async def get_trending_items():
    try:
        result = get_trending_entries()
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/update_trending")
async def update_trending(request: Request, token: str = Depends(token_query)):
    try:
        payload = await request.json()
        if not isinstance(payload, dict) or "movie" not in payload or "show" not in payload:
            raise ValueError("Payload must contain 'movie' and 'show' lists")

        movie_ids = [int(mid) for mid in payload.get("movie", [])]
        show_ids = [int(sid) for sid in payload.get("show", [])]

        config = ConfigDatabase()
        save_result = config.save_trending_config(movie_ids, show_ids)

        if save_result["status"] in ["inserted", "updated"]:
            update_trending_cache()
            result = get_trending_entries({"movie": movie_ids, "show": show_ids})
            return JSONResponse(content={"status": "success", "data": result})
        else:
            raise Exception(save_result.get('message', 'Unknown error'))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/similar")
async def get_similar_media(
    media_type: str = Query(..., description="Type of media: 'movie' or 'show'"),
    genres: List[str] = Query(..., description="Genres to search for (max 2)", max_length=2),
):
    if media_type not in ["movie", "show"]:
        raise HTTPException(status_code=400, detail="Media type must be 'movie' or 'show'")
    if not genres or len(genres) > 2:
        raise HTTPException(status_code=400, detail="Must provide 1-2 genre keywords")
    try:
        results = get_similar_by_genre(media_type, genres)
        return JSONResponse(content=results or [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/search")
async def search_all(
    query: str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(20, ge=1, le=50, description="Maximum results per media type"),
):
    if len(query) < 2:
        return JSONResponse(content=[])
    try:
        results = await get_cached_search_results(query, limit)
        return JSONResponse(content=results)
    except Exception as e:
        LOGGER.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# --- Streaming Handler (SECURE) ---

@app.get("/api/v1/dl/{id}")
async def stream_handler(
    request: Request,
    id: str,
    token: str = Query(None, description="JWT stream token"),
    media_type: str = Query(None, description="Type of media: 'movie' or 'show'"),
    quality_index: int = Query(None, description="Index of the quality option to select"),
    season_number: Optional[int] = Query(None, description="Season number"),
    episode_number: Optional[int] = Query(None, description="Episode number"),
):
    """
    Stream movie or show content using JWT token authentication.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Stream token required")

    try:
        token_data = verify_stream_token(token)
        token_id = str(token_data.get("id", ""))
        token_file_id = str(token_data.get("fileId", ""))
        
        token_media_type = token_data.get("mediaType")
        token_quality_index = token_data.get("qualityIndex", 0)
        token_season_number = token_data.get("seasonNumber")
        token_episode_number = token_data.get("episodeNumber")

        # Authorization Logic
        is_bundle = False
        # Allow if token explicitly authorizes this File ID (Bundle)
        if token_file_id and token_file_id == id:
            is_bundle = True
        # Allow if token authorizes the Content ID (Movie/Show)
        elif token_id != id:
            LOGGER.warning(f"Token mismatch: ID={id}, TokenID={token_id}, TokenFileID={token_file_id}")
            raise HTTPException(status_code=401, detail="Token ID mismatch")

        if not is_bundle:
            media_type = token_media_type
            quality_index = token_quality_index
            season_number = token_season_number
            episode_number = token_episode_number

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation error: {str(e)}")

    try:
        # Handle Bundle/Direct File Request
        if is_bundle:
            LOGGER.info(f"Looking up bundle for hash/id: {id}")
            
            # 1. Look up by HASH first (Short ID)
            bundle = bundle_db.collection.find_one({"file_hash": id})
            
            # 2. Fallback to File ID (Long ID)
            if not bundle:
                bundle = bundle_db.collection.find_one({"file_id": id})
            
            if not bundle:
                 LOGGER.error(f"Bundle not found in DB for: {id}")
                 raise HTTPException(status_code=404, detail="Bundle file not found")
            
            msg_id = int(bundle.get("msg_id"))
            chat_id = int(bundle.get("chat_id"))
            
            # SECURITY FIX: Retrieve the Secure Hash from DB
            secure_hash = bundle.get("file_hash")
            
            if not secure_hash:
                # Compatibility Mode: If legacy bundle has no hash, we Log it but Allow it.
                # Passing None to media_streamer skips the hash check (Original behavior for bundles)
                LOGGER.warning(f"Bundle {id} has no hash in DB. Integrity check skipped (Legacy Support).")
                secure_hash = None 

            return await media_streamer(request, chat_id, msg_id, secure_hash=secure_hash)

        # Handle Standard Movie/Show Request
        else:
            from utils.api.get_video import get_video_details
            file_details = await get_video_details(
                id, media_type, quality_index, season_number, episode_number
            )

            msg_id = int(file_details["msg_id"])
            chat_id = int(file_details["chat_id"])
            file_hash = file_details["hash"]

            return await media_streamer(request, chat_id, msg_id, secure_hash=file_hash)

    except TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Streaming service temporarily unavailable. Please try again."
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        LOGGER.exception("Stream Handler Error")
        raise HTTPException(status_code=500, detail=f"Error streaming content: {str(e)}")


async def media_streamer(request: Request, chat_id: int, id: int, secure_hash: str = None):
    range_header = request.headers.get("Range", 0)

    if not work_loads:
        LOGGER.warning("No clients available in work_loads dictionary")

    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]

    if index not in multi_clients:
        LOGGER.error(f"Client index {index} not found in multi_clients")
        raise HTTPException(status_code=503, detail="Streaming client configuration error")

    LOGGER.debug(f"Client {index} serving {request.client.host}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]["object"]
    else:
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = {"object": tg_connect, "timestamp": time.time()}

    try:
        file_id = await tg_connect.get_file_properties(chat_id=chat_id, message_id=id)
    except Exception as e:
        LOGGER.error(f"Error getting file properties: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving file: {str(e)}")

    # SECURITY CHECK: Verify File Integrity
    if secure_hash:
        # Check first 6 chars of unique_id against our DB hash
        if file_id.unique_id[:6] != secure_hash:
            LOGGER.critical(f"Hash Mismatch! Expected: {secure_hash}, Got: {file_id.unique_id[:6]}")
            # This prevents streaming if the file was swapped/changed
            raise InvalidHash
    else:
         LOGGER.debug("Skipping hash check (No secure_hash provided)")

    file_size = file_id.file_size
    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = 0
        until_bytes = file_size - 1

    if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return StreamingResponse(
            content=(f"416: Range not satisfiable",),
            status_code=416,
            headers={"Content-Range": f"bytes */{file_size}"},
        )
        
    chunk_size = min(1024 * 1024, file_size // 10)
    until_bytes = min(until_bytes, file_size - 1)
    
    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1
    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)

    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
    )

    mime_type = file_id.mime_type
    file_name = file_id.file_name
    disposition = "attachment"

    if not mime_type:
        if file_name:
            mime_type = mimetypes.guess_type(file_name)[0]
        else:
            mime_type = "application/octet-stream"
            file_name = f"{secrets.token_hex(2)}.unknown"
    elif not file_name:
        file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"

    return StreamingResponse(
        status_code=206 if range_header else 200,
        content=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Type",
        },
    )

def clean_cache():
    current_time = time.time()
    expired_keys = [k for k, v in class_cache.items() if current_time - v["timestamp"] > 3600]
    for key in expired_keys:
        del class_cache[key]

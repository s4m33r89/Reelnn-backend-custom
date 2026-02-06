
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from os import path as ospath
from app import LOGGER
from pyrogram import Client
from utils.utils import check_quality
from pyrogram.types import Message
from pymediainfo import MediaInfo  

def gen_media_info(media_info):
    """Extract media information from pymediainfo output"""
    info = {
        "file_type": "N/A",
        "video_codec": "N/A",
        "audio":  "N/A",
        "subtitle": "N/A"
    }
    
    for track in media_info.tracks:
        if track.track_type == 'General':
            info["file_type"] = track.format.lower() if hasattr(track, 'format') else "N/A"
            info["audio"] = track.audio_language_list if hasattr(track, 'audio_language_list') else "N/A"
            
        elif track.track_type == 'Video':
            info["video_codec"] = track.encoded_library_name if hasattr(track, 'encoded_library_name') else "N/A"
            
        elif track.track_type == 'Text' or track.track_type == 'Subtitle':
            info["subtitle"] = track.format if hasattr(track, 'format') else "N/A"
            
    
    return info


async def media_quality(client: Client, message: Message) -> tuple:
    temp_file = None
    try:
        
        path = "mediainfo/"
        if not await aiopath.isdir(path):
            await mkdir(path)
        file = message.video or message.document or message.animation
        
        temp_file = ospath.join(path, f"sample_{file.file_id[:12]}")
        
        
        async for chunk in client.stream_media(message, limit=1):
            async with aiopen(temp_file, "wb") as f:
                await f.write(chunk)
                break  
        
        
        if not await aiopath.exists(temp_file):
            LOGGER.error(f"Downloaded file not found at {temp_file}")
            return None, None
        
        
        media_info = MediaInfo.parse(temp_file)
        
        
        stdout = ""
        for track in media_info.tracks:
            if track.track_type == 'Video' and hasattr(track, 'height'):
                stdout += f"Image height: {track.height}\n"
        
        
        quality = check_quality(stdout)
        media_info_result = gen_media_info(media_info)
        
        
        result = {
            "file_type": media_info_result["file_type"],
            "video_codec": media_info_result["video_codec"],
            "audio": media_info_result["audio"],
            "subtitle": media_info_result["subtitle"]
        }
        return quality, result
        
    except Exception as e:
        LOGGER.error(f"Media quality extraction failed: {str(e)}")
        return None, None
        
    finally:
        
        if temp_file and await aiopath.exists(temp_file):
            try:
                await aioremove(temp_file)
            except Exception as e:
                LOGGER.warning(f"Failed to remove temporary file {temp_file}: {str(e)}")
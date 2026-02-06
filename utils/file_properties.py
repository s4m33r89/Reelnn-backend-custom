
# Credits:
# This code is adapted from TechZIndex by TechShreyash ([GitHub Username])
# Source: https://github.com/TechShreyash/TechZIndex
# Also thanks to the https://github.com/weebzone/Surf-TG
# Licensed under [License Name] (see LICENSE file in the original repository)

from pyrogram.file_id import FileId
from typing import Optional
from pyrogram import Client
from utils.exceptions import FileNotFound

def is_media(message):
    return next((getattr(message, attr) for attr in ["document", "photo", "video", "audio", "voice", "video_note", "sticker", "animation"] if getattr(message, attr)), None)

async def get_file_ids(client: Client, chat_id: int, message_id: int) -> Optional[FileId]:
    message = await client.get_messages(chat_id, message_id)
    if message.empty:
        raise FileNotFound
    file_id = file_unique_id = None
    if media := is_media(message):
        file_id, file_unique_id = FileId.decode(
            media.file_id), media.file_unique_id
    setattr(file_id, 'file_name', getattr(media, 'file_name', ''))
    setattr(file_id, 'file_size', getattr(media, 'file_size', 0))
    setattr(file_id, 'mime_type', getattr(media, 'mime_type', ''))
    setattr(file_id, 'unique_id', file_unique_id)
    return file_id
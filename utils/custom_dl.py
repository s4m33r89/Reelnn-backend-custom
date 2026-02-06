# Credits:
# This code is adapted from TechZIndex by TechShreyash ([GitHub Username])
# Source: https://github.com/TechShreyash/TechZIndex
# Also thanks to the https://github.com/weebzone/Surf-TG
# Licensed under [License Name] (see LICENSE file in the original repository)

import asyncio
import logging
from pyrogram import utils, raw
from pyrogram.errors import AuthBytesInvalid
from pyrogram.file_id import FileId, FileType, ThumbnailSource
from pyrogram.session import Session, Auth
from typing import Dict, Union, AsyncGenerator
from utils.exceptions import FileNotFound
from utils.file_properties import get_file_ids
from app import work_loads
from pyrogram import Client, utils, raw


class ByteStreamer:
    def __init__(self, client: Client):
        self.clean_timer = 30 * 60
        self.client: Client = client
        self.__cached_file_ids: Dict[int, FileId] = {}
        self.__file_properties_cache: Dict[tuple, FileId] = {}  # Manual cache
        asyncio.create_task(self.clean_cache())

    async def get_file_properties(self, chat_id: int, message_id: int) -> FileId:
        cache_key = (chat_id, message_id)
        if cache_key in self.__file_properties_cache:
            return self.__file_properties_cache[cache_key]

        if message_id not in self.__cached_file_ids:
            file_id = await get_file_ids(self.client, int(chat_id), int(message_id))
            if not file_id:
                logging.info('Message with ID %s not found!', message_id)
                raise FileNotFound
            self.__cached_file_ids[message_id] = file_id

        file_id = self.__cached_file_ids[message_id]
        self.__file_properties_cache[cache_key] = file_id
        return file_id

    async def yield_file(self, file_id: FileId, index: int, offset: int, first_part_cut: int, last_part_cut: int, part_count: int, chunk_size: int) -> AsyncGenerator[bytes, None]:
        client = self.client
        work_loads[index] += 1
        logging.debug(f"Starting to yield file with client {index}.")
        media_session = await self.generate_media_session(client, file_id)
        current_part = 1
        location = await self.get_location(file_id)
        try:
            while current_part <= part_count:
                # Retry logic for handling timeouts
                max_retries = 3
                retry_count = 0
                retry_delay = 1  # Initial delay in seconds
                
                while True:
                    try:
                        r = await media_session.send(raw.functions.upload.GetFile(
                            location=location, offset=offset, limit=chunk_size))
                        break  # Success - exit retry loop
                    except TimeoutError:
                        retry_count += 1
                        if retry_count > max_retries:
                            logging.error(f"Request timed out after {max_retries} retries at offset {offset}")
                            raise  # Re-raise if we've exhausted retries
                        
                        logging.warning(f"Request timed out, retrying ({retry_count}/{max_retries}) at offset {offset}")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                
                if isinstance(r, raw.types.upload.File):
                    chunk = r.bytes
                    if not chunk:
                        break
                    if part_count == 1:
                        yield chunk[first_part_cut:last_part_cut]
                    elif current_part == 1:
                        yield chunk[first_part_cut:]
                    elif current_part == part_count:
                        yield chunk[:last_part_cut]
                    else:
                        yield chunk

                    current_part += 1
                    offset += chunk_size
                    logging.debug(f"Yielded part {current_part-1}/{part_count}, offset {offset}")
                else:
                    logging.error("Unexpected response type from Telegram")
                    break
        except Exception as e:
            logging.error(f"Error while streaming file: {e}")
            raise
        finally:
            logging.debug(f"Finished yielding file with {current_part-1} parts.")
            work_loads[index] -= 1


    async def generate_media_session(self, client: Client, file_id: FileId) -> Session:
        media_session = client.media_sessions.get(file_id.dc_id, None)
        if (media_session is None):
            if file_id.dc_id != await client.storage.dc_id():
                media_session = Session(client,
                                        file_id.dc_id,
                                        await Auth(client, file_id.dc_id, await client.storage.test_mode()).create(),
                                        await client.storage.test_mode(),
                                        is_media=True)
                await media_session.start()
                for _ in range(6):
                    exported_auth = await client.invoke(raw.functions.auth.ExportAuthorization(dc_id=file_id.dc_id))
                    try:
                        await media_session.send(raw.functions.auth.ImportAuthorization(id=exported_auth.id, bytes=exported_auth.bytes))
                        break
                    except AuthBytesInvalid:
                        logging.debug(
                            'Invalid authorization bytes for DC %s!', file_id.dc_id)
                        continue
                else:
                    await media_session.stop()
                    raise AuthBytesInvalid
            else:
                media_session = Session(client,
                                        file_id.dc_id,
                                        await client.storage.auth_key(),
                                        await client.storage.test_mode(),
                                        is_media=True)
                await media_session.start()
            logging.debug(f"Created media session for DC {file_id.dc_id}")
            client.media_sessions[file_id.dc_id] = media_session
        else:
            logging.debug(f"Using cached media session for DC {file_id.dc_id}")
        return media_session

    @staticmethod
    async def get_location(file_id: FileId) -> Union[raw.types.InputPhotoFileLocation, raw.types.InputDocumentFileLocation, raw.types.InputPeerPhotoFileLocation]:
        file_type = file_id.file_type
        if file_type == FileType.CHAT_PHOTO:
            if file_id.chat_id > 0:
                peer = raw.types.InputPeerUser(
                    user_id=file_id.chat_id, access_hash=file_id.chat_access_hash)
            else:
                if file_id.chat_access_hash == 0:
                    peer = raw.types.InputPeerChat(chat_id=-file_id.chat_id)
                else:
                    peer = raw.types.InputPeerChannel(channel_id=utils.get_channel_id(
                        file_id.chat_id), access_hash=file_id.chat_access_hash)
            location = raw.types.InputPeerPhotoFileLocation(peer=peer,
                                                            volume_id=file_id.volume_id,
                                                            local_id=file_id.local_id,
                                                            big=file_id.thumbnail_source == ThumbnailSource.CHAT_PHOTO_BIG)
        elif file_type == FileType.PHOTO:
            location = raw.types.InputPhotoFileLocation(id=file_id.media_id,
                                                        access_hash=file_id.access_hash,
                                                        file_reference=file_id.file_reference,
                                                        thumb_size=file_id.thumbnail_size)
        else:
            location = raw.types.InputDocumentFileLocation(id=file_id.media_id,
                                                           access_hash=file_id.access_hash,
                                                           file_reference=file_id.file_reference,
                                                           thumb_size=file_id.thumbnail_size)
        return location

    async def clean_cache(self) -> None:
        """
        function to clean the cache to reduce memory usage
        """
        while True:
            await asyncio.sleep(self.clean_timer)
            self.__cached_file_ids.clear()
            self.__file_properties_cache.clear()
            logging.debug("Cleaned the cache")
from pyrogram import Client
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import config

from config import SUDO_USERS


@Client.on_message(
    filters.command("use_caption", prefixes="/")
    & filters.private
    & filters.user(SUDO_USERS)
)
async def use_caption_command(client: Client, message: Message):

    status = "Enabled" if config.USE_CAPTION else "Disabled"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"Toggle Caption {'OFF' if config.USE_CAPTION else 'ON'}",
                    callback_data="toggle_caption",
                )
            ]
        ]
    )

    await message.reply_text(
        f"**Current Caption Status**: {status}\n\nUse the button below to toggle caption mode.",
        reply_markup=keyboard,
    )


@Client.on_callback_query(filters.regex("^toggle_caption$"))
async def toggle_caption_callback(client, callback_query):

    try:
        config.USE_CAPTION = not config.USE_CAPTION

        new_status = "Enabled" if config.USE_CAPTION else "Disabled"

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"Toggle Caption {'OFF' if config.USE_CAPTION else 'ON'}",
                        callback_data="toggle_caption",
                    )
                ]
            ]
        )

        await callback_query.message.edit_text(
            f"**Caption Status**: {new_status}\n\nUse the button below to toggle caption mode.",
            reply_markup=keyboard,
        )

        await callback_query.answer(
            f"Caption mode {new_status}. Change is temporary and will reset on restart."
        )

    except Exception as e:

        await callback_query.answer(f"Error: {str(e)}", show_alert=True)

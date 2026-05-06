import logging
from pyrogram import Client
from pyrogram.handlers import MessageHandler

logger = logging.getLogger(__name__)


@Client.on_message()
async def catch_all(bot, message):
    pass

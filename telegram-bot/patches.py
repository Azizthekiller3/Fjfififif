"""
Monkey-patch Pyrogram's dispatcher to gracefully handle
'Peer id invalid' ValueErrors that occur during Message._parse.

Without this patch, any group message whose reply_to_message
references an unresolvable peer silently kills the update
dispatcher, causing the bot to stop responding entirely.
"""
import logging
from pyrogram.dispatcher import Dispatcher

logger = logging.getLogger(__name__)

_orig_process_update = Dispatcher.process_update


async def _safe_process_update(self, update, users, chats):
    try:
        return await _orig_process_update(self, update, users, chats)
    except ValueError as e:
        if "Peer id invalid" in str(e):
            logger.warning("Skipping update — unresolvable peer: %s", e)
            return
        raise
    except Exception as e:
        logger.error("Unhandled exception in dispatcher: %s", e, exc_info=True)


Dispatcher.process_update = _safe_process_update
logger.info("✅ Pyrogram dispatcher patched — peer-id errors will be skipped safely")

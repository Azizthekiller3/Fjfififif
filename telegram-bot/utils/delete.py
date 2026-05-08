"""
Auto-delete worker — legacy standalone entry point.

The auto-delete loop now runs as an asyncio task inside bot.py
using the main bot instance (_autodelete_loop). This file is kept
for backwards compatibility but is no longer launched as a subprocess.
"""
import asyncio
import logging
import sys
import os
from time import time

logger = logging.getLogger(__name__)


async def run_check_up(bot=None):
    """
    Run the auto-delete loop.

    If `bot` is provided (a connected Pyrogram Client), use it directly.
    Otherwise (legacy standalone mode) this function does nothing — the
    loop is now managed inside bot.py to avoid dual-session conflicts.
    """
    if bot is None:
        logger.warning(
            "run_check_up() called without a bot instance. "
            "Auto-delete is now handled inside bot.py as an asyncio task."
        )
        return

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import get_all_dlt_data, delete_all_dlt_data
    from pyrogram.errors import FloodWait

    logger.info("Auto-delete worker running (in-process mode)")
    while True:
        try:
            now = int(time())
            records = await get_all_dlt_data(now)
            for data in records:
                try:
                    await bot.delete_messages(
                        chat_id=data["chat_id"],
                        message_ids=data["message_id"],
                    )
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except Exception as e:
                    logger.debug(f"Delete skip: {data} — {e}")
            if records:
                await delete_all_dlt_data(now)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Auto-delete loop error: {e}")
        await asyncio.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.warning(
        "Direct execution of utils/delete.py is disabled — "
        "auto-delete now runs inside the main bot process."
    )

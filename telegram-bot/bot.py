import patches  # noqa: F401 — must be first

import asyncio
import logging
import os
import signal
import sys

from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, SESSION, LOG_CHANNEL, OWNER_ID
from database import create_indexes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

_USER_CONNECTED = False
_KEEPALIVE_INTERVAL = 240  # 4 minutes — shorter than Railway's ~5 min idle TCP timeout


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"},
            sleep_threshold=60,
            in_memory=True,
        )

    async def start(self):
        await super().start()
        await create_indexes()

        global _USER_CONNECTED
        if SESSION:
            await _start_user_session()
        else:
            logger.warning("⚠️ No SESSION set — search will be limited.")

        from pyrogram.types import BotCommand
        await self.set_bot_commands([
            BotCommand("start",        "Check If I'm Alive or Not!"),
            BotCommand("id",           "Get Channel/Group Id"),
            BotCommand("verify",       "Send in group & wait for It To Accept"),
            BotCommand("connect",      "Link Database Channel/Group to search from"),
            BotCommand("disconnect",   "Disconnect Database"),
            BotCommand("fsub",         "Add a Force Subscribe Channel"),
            BotCommand("nofsub",       "Remove Force Subscribe Channel"),
            BotCommand("connections",  "Get connected channels list"),
            BotCommand("autodelete",   "Set auto-delete timer"),
            BotCommand("help",         "Show all commands"),
            BotCommand("ping",         "Check bot speed and latency"),
            BotCommand("logs",         "View bot status & logs (owner only)"),
        ])
        logger.info("✅ Bot commands registered")

        me = await self.get_me()
        logger.info(f"✅ Bot started as @{me.username} (id={me.id})")

        if LOG_CHANNEL:
            try:
                await self.send_message(
                    LOG_CHANNEL,
                    f"✅ <b>Bot Started</b>\n\n🤖 @{me.username} (<code>{me.id}</code>)",
                )
            except Exception:
                pass

    async def stop(self, *args):
        if SESSION:
            try:
                from client import User
                if User.is_connected:
                    await User.stop()
            except Exception:
                pass
        await super().stop()
        logger.info("Bot stopped")


async def _start_user_session():
    global _USER_CONNECTED
    try:
        from client import User
        if not User.is_connected:
            await User.start()
        me = await User.get_me()
        _USER_CONNECTED = True
        logger.info(f"✅ User session started as @{me.username or me.first_name}")
        try:
            count = 0
            async for _ in User.get_dialogs():
                count += 1
                if count >= 200:
                    break
            logger.info(f"✅ Peer cache warmed up ({count} dialogs)")
        except Exception as warm_err:
            logger.warning(f"Peer cache warm-up partial: {warm_err}")
    except Exception as e:
        _USER_CONNECTED = False
        logger.warning(f"⚠️ User session failed: {e}")


async def _session_watchdog():
    """Reconnect the user (search) session if it drops."""
    while True:
        await asyncio.sleep(300)
        if not SESSION:
            continue
        try:
            from client import User
            if not User.is_connected:
                logger.warning("Session watchdog: User disconnected — reconnecting…")
                await _start_user_session()
            else:
                await User.get_me()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Session watchdog error: {e}")
            try:
                await _start_user_session()
            except Exception:
                pass


async def _bot_keepalive(bot: Client):
    """
    Ping Telegram every 4 minutes so Railway's TCP idle timeout never closes
    the MTProto connection.  After 3 consecutive failures the task raises so
    the bot process exits and Railway restarts it.
    """
    failures = 0
    while True:
        await asyncio.sleep(_KEEPALIVE_INTERVAL)
        try:
            await bot.get_me()
            failures = 0
            logger.debug("Keepalive OK")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            failures += 1
            logger.warning(f"Keepalive failed ({failures}/3): {e}")
            if failures >= 3:
                logger.error("Bot connection lost — exiting so Railway can restart")
                os._exit(1)   # force Railway to do a clean restart


async def _autodelete_loop(bot: Client):
    """
    Delete expired messages using the MAIN bot instance.
    No subprocess, no second BOT_TOKEN session — avoids the update-stealing bug.
    """
    from time import time as _time
    from database import get_all_dlt_data, delete_all_dlt_data
    from pyrogram.errors import FloodWait

    logger.info("✅ Auto-delete task started")
    while True:
        try:
            now = int(_time())
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
                    logger.debug(f"Auto-delete skip: {data} — {e}")
            if records:
                await delete_all_dlt_data(now)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Auto-delete loop error: {e}")
        await asyncio.sleep(5)


async def main():
    from health import start_health_server
    start_health_server()

    bot = Bot()
    await bot.start()

    # Background tasks — same pattern as original watchdog
    watchdog  = asyncio.create_task(_session_watchdog())
    keepalive = asyncio.create_task(_bot_keepalive(bot))
    autodelete = asyncio.create_task(_autodelete_loop(bot))

    stop_event = asyncio.Event()

    def _handle_signal():
        logger.info("Shutdown signal — stopping…")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass

    logger.info("Bot is running. SIGTERM or Ctrl+C to stop.")
    await stop_event.wait()

    for task in (autodelete, keepalive, watchdog):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    await bot.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user")

import patches  # noqa: F401 — must be first: patches Pyrogram dispatcher

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
_BOT_RESTART_DELAY = 10   # seconds between crash-restarts
_KEEPALIVE_INTERVAL = 240 # ping Telegram every 4 minutes to keep MTProto alive


def _session_name():
    sessions_dir = os.environ.get("SESSIONS_DIR", "sessions")
    try:
        os.makedirs(sessions_dir, exist_ok=True)
        test = os.path.join(sessions_dir, ".write_test")
        open(test, "w").close()
        os.remove(test)
        return os.path.join(sessions_dir, "bot")
    except Exception:
        return ":memory:"


class Bot(Client):
    def __init__(self):
        name = _session_name()
        kwargs = dict(
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"},
            sleep_threshold=60,
        )
        if name == ":memory:":
            kwargs["in_memory"] = True
            name = "bot"
        super().__init__(name=name, **kwargs)

    async def start(self):
        await super().start()
        await create_indexes()

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


async def _bot_keepalive(bot: "Bot"):
    """
    Ping Telegram every 4 minutes to prevent the MTProto TCP connection
    from being silently dropped by Railway's network (idle timeout ~5 min).
    If the ping fails, attempt a reconnect.
    """
    consecutive_failures = 0
    while True:
        await asyncio.sleep(_KEEPALIVE_INTERVAL)
        try:
            await bot.get_me()
            consecutive_failures = 0
            logger.debug("Keepalive ping OK")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            consecutive_failures += 1
            logger.warning(f"Keepalive ping failed ({consecutive_failures}x): {e}")
            if consecutive_failures >= 3:
                logger.error("Bot appears disconnected — triggering restart")
                # Raise so the supervisor (main) restarts the whole bot
                raise RuntimeError(f"Bot keepalive failed 3 times: {e}")


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
            logger.warning(f"Session watchdog error: {e} — attempting reconnect")
            try:
                await _start_user_session()
            except Exception:
                pass


async def _autodelete_loop(bot: "Bot"):
    """
    Delete expired messages using the MAIN bot instance.
    Runs as an asyncio task — no subprocess, no second bot token connection.
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


async def _run_bot():
    """Start the bot and run until a stop signal or fatal error."""
    bot = Bot()
    await bot.start()

    tasks = [
        asyncio.create_task(_bot_keepalive(bot),    name="keepalive"),
        asyncio.create_task(_session_watchdog(),     name="watchdog"),
        asyncio.create_task(_autodelete_loop(bot),   name="autodelete"),
    ]

    stop_event = asyncio.Event()

    def _handle_signal():
        logger.info("Shutdown signal received — stopping bot…")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass

    logger.info("Bot is running. Send SIGTERM or Ctrl+C to stop.")

    # Wait until stop signal OR any background task crashes
    done, pending = await asyncio.wait(
        [asyncio.create_task(stop_event.wait()), *tasks],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # Cancel remaining tasks
    for task in pending:
        task.cancel()
    for task in pending:
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    # Check if a task crashed (vs clean shutdown)
    for task in done:
        if not task.cancelled() and task.exception():
            exc = task.exception()
            logger.error(f"Task '{task.get_name()}' crashed: {exc}")
            await bot.stop()
            raise exc  # propagate to supervisor

    await bot.stop()


async def main():
    from health import start_health_server
    start_health_server()

    attempt = 0
    while True:
        attempt += 1
        try:
            logger.info(f"🚀 Starting bot (attempt #{attempt})")
            await _run_bot()
            logger.info("Bot exited cleanly.")
            break  # clean exit (SIGTERM/SIGINT) — don't restart
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(
                f"Bot crashed: {e} — restarting in {_BOT_RESTART_DELAY}s "
                f"(attempt #{attempt})"
            )
            await asyncio.sleep(_BOT_RESTART_DELAY)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user")

import asyncio
import logging
import os
import signal
import sys
from subprocess import Popen

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


def _session_name():
    """Use a file session when a writable sessions dir exists, else in-memory."""
    import os
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

        global _USER_CONNECTED
        if SESSION:
            await _start_user_session()
        else:
            logger.warning("⚠️ No SESSION set — search will be limited.")

        _start_autodelete_worker()

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
        except Exception as e:
            logger.warning(f"Session watchdog error: {e} — attempting reconnect")
            try:
                await _start_user_session()
            except Exception:
                pass


def _start_autodelete_worker():
    try:
        bot_dir = os.path.dirname(os.path.abspath(__file__))
        Popen(
            [sys.executable, "-m", "utils.delete"],
            cwd=bot_dir,
        )
        logger.info("✅ Auto-delete worker started")
    except Exception as e:
        logger.warning(f"Auto-delete worker failed to start: {e}")


async def main():
    from health import start_health_server
    start_health_server()

    bot = Bot()
    await bot.start()

    watchdog = asyncio.create_task(_session_watchdog())

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
    await stop_event.wait()

    watchdog.cancel()
    try:
        await watchdog
    except asyncio.CancelledError:
        pass
    await bot.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user")

import asyncio
import logging
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
            async for _ in User.get_dialogs():
                pass
            logger.info("✅ Peer cache warmed up")
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
        Popen(
            [sys.executable, "-m", "utils.delete"],
            cwd=".",
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

    logger.info("Bot is running. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
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

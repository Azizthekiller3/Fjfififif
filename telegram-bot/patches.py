"""
Pyrogram 2.0.106 compatibility stub.

In pyrogram==2.0.106 the Dispatcher.handler_worker already catches
all exceptions (including ValueError 'Peer id invalid') with a broad
except clause, so no monkey-patching is required.

This file exists so bot.py can safely `import patches` without errors.
"""
import logging

logging.getLogger(__name__).info(
    "patches.py loaded — pyrogram==2.0.106 handles dispatcher errors natively"
)

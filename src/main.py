"""
Main entry point for the Discord bot with enhanced configuration.
"""

import os
import sys
import logging
import asyncio
import traceback
from datetime import datetime

from dotenv import load_dotenv

from utils.logging_manager import LoggingManager
from utils.settings import (
    BOT_TOKEN,
    BOT_VERSION,
    LOG_LEVEL,
    LOG_TO_FILE,
    LOG_FILE_PATH,
    GUILD_ID,
)
from bot import bot

# Configure application startup path
APP_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(APP_PATH, "..", "data")
LOGS_PATH = os.path.join(APP_PATH, "..", "logs")

# Ensure necessary directories exist
os.makedirs(LOGS_PATH, exist_ok=True)
os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(os.path.join(APP_PATH, "cogs"), exist_ok=True)

# Load environment variables
load_dotenv()

# Set up logging with timestamp
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f"{LOG_FILE_PATH.rsplit('.', 1)[0]}_{current_time}.log"

logger = LoggingManager.setup_logger(
    name="main",
    console_output=True,
    file_output=LOG_TO_FILE,
    filename=log_filename,
    file_mode="w",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
)


async def main():
    """Asynchronous main entry point for the bot."""
    # Check for required token
    if not BOT_TOKEN:
        logger.critical("No BOT_TOKEN found in environment variables!")
        return

    try:
        logger.info(f"Starting Discord bot v{BOT_VERSION}")
        logger.info(f"Python version: {sys.version}")

        # Print summary of loaded modules
        logger.info(f"Bot prefix: {bot.command_prefix}")
        logger.info(f"Loading extensions: {', '.join(bot.startup_extensions)}")

        if GUILD_ID:
            logger.info(f"Running in single guild mode with ID: {GUILD_ID}")
        else:
            logger.warning("No GUILD_ID set - bot will operate in multi-guild mode")

        # Start the bot with error handling
        try:
            async with bot:
                await bot.start(BOT_TOKEN)
        except Exception as e:
            logger.critical(f"Bot crashed: {str(e)}")
            logger.critical(traceback.format_exc())

    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Failed to start bot: {str(e)}")
        logger.critical(traceback.format_exc())


def cli_startup():
    """Command-line interface entry point."""
    # Print banner
    banner = f"""
    ╔═══════════════════════════════════════════╗
    ║            Discord Multi-Bot              ║
    ║             Version {BOT_VERSION:<10}            ║
    ║        Starting bot services...           ║
    ╚═══════════════════════════════════════════╝
    """
    print(banner)

    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot shutdown requested by user.")
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    cli_startup()

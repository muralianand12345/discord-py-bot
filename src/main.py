"""
Main entry point for the Discord bot.
"""

import os
import logging
from dotenv import load_dotenv

from utils.logging_manager import LoggingManager
from utils.settings import BOT_TOKEN, LOG_LEVEL, LOG_TO_FILE, LOG_FILE_PATH
from bot import bot

# Ensure logs and data directories exist
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Ensure cogs directory exists
os.makedirs("src/cogs", exist_ok=True)

# Load environment variables
load_dotenv()

# Set up logging
logger = LoggingManager.setup_logger(
    name="main",
    console_output=True,
    file_output=LOG_TO_FILE,
    filename=LOG_FILE_PATH,
    file_mode="w",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
)


def main():
    """Main entry point for the bot."""
    # Check for required token
    if not BOT_TOKEN:
        logger.critical("No BOT_TOKEN found in environment variables!")
        return

    try:
        logger.info("Starting bot...")

        # Print summary of loaded modules
        logger.info(f"Bot prefix: {bot.command_prefix}")
        logger.info(f"Starting version: {bot.app_version}")
        logger.info(f"Loading extensions: {', '.join(bot.startup_extensions)}")

        # Start the bot
        bot.run(BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.critical(f"Failed to start bot: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()

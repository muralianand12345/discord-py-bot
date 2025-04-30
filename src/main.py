"""
Main entry point for the Discord bot.
"""

import os
import sys
import logging
import asyncio
from dotenv import load_dotenv

from utils.logging_manager import LoggingManager
from utils.settings import BOT_TOKEN, LOG_LEVEL, LOG_TO_FILE, LOG_FILE_PATH
from bot import bot

# Ensure proper directory structure
os.makedirs("logs", exist_ok=True)

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


def check_environment() -> bool:
    """
    Check if all required environment variables are set.

    Returns:
        bool: True if all required variables are set, False otherwise
    """
    missing_vars = []

    # Check for required variables
    if not BOT_TOKEN:
        missing_vars.append("BOT_TOKEN")

    # Log warnings for missing optional variables
    if not os.getenv("GROQ_API_KEY"):
        logger.warning(
            "GROQ_API_KEY is not set. The bot will use romanization fallback."
        )

    # Return result for required variables
    if missing_vars:
        logger.critical(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        return False
    return True


async def main():
    """
    Main async entry point for the bot.
    """
    # Check environment
    if not check_environment():
        logger.critical("Environment check failed. Exiting.")
        sys.exit(1)

    try:
        logger.info("Starting bot...")
        async with bot:
            await bot.start(BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
        if bot.is_closed():
            logger.info("Bot was already closed.")
        else:
            logger.info("Closing bot connection...")
            await bot.close()
    except Exception as e:
        logger.critical(f"Failed to start bot: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())

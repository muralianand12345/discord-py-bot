import os
from dotenv import load_dotenv
from bot import bot
from utils.logging_manager import LoggingManager

# Load environment variables
load_dotenv()

# Set up logging
logger = LoggingManager.setup_logger(
    name="main",
    console_output=True,
    file_output=True,
    filename="logs/main.log",
    file_mode="w",
)


def main():
    """Main entry point for the bot."""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.critical("No BOT_TOKEN found in environment variables!")
        exit(1)

    try:
        logger.info("Starting bot...")
        bot.run(bot_token)
    except Exception as e:
        logger.critical(f"Failed to start bot: {str(e)}")


if __name__ == "__main__":
    main()

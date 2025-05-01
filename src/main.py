import asyncio
import traceback

from config import BOT
from bot import bot, logger


async def main():

    if not BOT.BOT_TOKEN:
        logger.critical("No BOT_TOKEN found in environment variables!")
        return

    if not BOT.GUILD_ID:
        logger.critical("No GUILD_ID found in environment variables!")
        return

    try:
        async with bot:
            await bot.start(BOT.BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Bot crashed: {str(e)}")
        logger.critical(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())

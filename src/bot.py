import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from typing import Optional
from utils.logging_manager import LoggingManager
from utils.translate import Translate

# Load environment variables
load_dotenv()

# Set up logging
logger = LoggingManager.setup_logger(
    name="jp_name_bot",
    console_output=True,
    file_output=True,
    filename="logs/bot.log",
    file_mode="w",
)

# Configure bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Required for prefixed commands

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    logger.info(f"Bot is ready: {bot.user}")


@bot.event
async def on_member_join(member: discord.Member):
    """Handle new member joining by translating their display name to Japanese."""
    original_name = member.display_name
    japanese_name = await Translate.to_japanese(original_name)

    try:
        await member.edit(nick=japanese_name)
        logger.info(f"Changed {original_name}'s nickname to {japanese_name}")
    except discord.Forbidden:
        logger.warning(f"No permission to change nickname for {original_name}")
    except Exception as e:
        logger.error(f"Error changing nickname: {str(e)}")


@bot.command(name="translate_name")
@commands.has_permissions(manage_nicknames=True)
async def translate_name(
    ctx: commands.Context, member: Optional[discord.Member] = None
):
    """
    Translate a member's name to Japanese.

    If no member is specified, translates the command author's name.

    Args:
        ctx: The command context
        member: The member whose name should be translated (optional)
    """
    target = member or ctx.author
    original_name = target.display_name
    japanese_name = await Translate.to_japanese(original_name)

    try:
        await target.edit(nick=japanese_name)
        await ctx.send(f"Changed {original_name}'s nickname to {japanese_name}")
        logger.info(f"Manually changed {original_name}'s nickname to {japanese_name}")
    except discord.Forbidden:
        await ctx.send(f"I don't have permission to change {original_name}'s nickname.")
        logger.warning(f"No permission to change nickname for {original_name}")
    except Exception as e:
        await ctx.send(f"Error changing nickname: {str(e)}")
        logger.error(f"Error changing nickname: {str(e)}")


@bot.command(name="translate_all")
@commands.has_permissions(administrator=True)
async def translate_all(ctx: commands.Context):
    """
    Translate all members' names to Japanese in the server.

    This command requires administrator permissions.

    Args:
        ctx: The command context
    """
    status_message = await ctx.send("Starting to translate all member names...")
    success_count = 0
    fail_count = 0

    for member in ctx.guild.members:
        if member.bot:
            continue

        original_name = member.display_name
        japanese_name = await Translate.to_japanese(original_name)

        try:
            await member.edit(nick=japanese_name)
            success_count += 1
            logger.info(
                f"Bulk translate: Changed {original_name}'s nickname to {japanese_name}"
            )
        except Exception as e:
            fail_count += 1
            logger.error(
                f"Bulk translate: Error changing {original_name}'s nickname: {str(e)}"
            )

    await status_message.edit(
        content=f"Finished translating names: {success_count} successful, {fail_count} failed."
    )
    logger.info(
        f"Bulk translate completed: {success_count} successful, {fail_count} failed."
    )


@bot.event
async def on_command_error(ctx: commands.Context, error):
    """Handle command errors."""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Member not found. Please mention a valid member.")
    else:
        await ctx.send(f"An error occurred: {str(error)}")
        logger.error(f"Command error: {str(error)}")

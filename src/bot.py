"""
Discord bot that translates usernames to Japanese using Groq LLM.
"""

import discord
import asyncio
from discord.ext import commands
from typing import Optional

from utils.logging_manager import LoggingManager
from utils.translate import Translate
from utils.settings import BOT_TOKEN, BOT_PREFIX

# Set up logging
logger = LoggingManager.setup_logger(
    name="discord_bot",
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
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)


@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    logger.info(f"Bot is ready: {bot.user}")
    logger.info(f"Using command prefix: {BOT_PREFIX}")


@bot.event
async def on_member_join(member: discord.Member):
    """
    Handle new member joining by translating their display name to Japanese.

    Args:
        member: The Discord member who joined
    """
    # Skip bots
    if member.bot:
        logger.debug(f"Skipping bot {member.display_name}")
        return

    original_name = member.display_name

    try:
        japanese_name = await Translate.to_japanese(original_name)

        # Ensure the name complies with Discord's requirements
        if not japanese_name or len(japanese_name) > 32:
            logger.warning(
                f"Invalid translated name for {original_name}: {japanese_name}"
            )
            # Truncate if too long
            if japanese_name and len(japanese_name) > 32:
                japanese_name = japanese_name[:32]

        # Apply the nickname if we have a valid translation
        if japanese_name and japanese_name != original_name:
            try:
                await member.edit(nick=japanese_name)
                logger.info(f"Changed {original_name}'s nickname to {japanese_name}")
            except discord.Forbidden:
                logger.warning(f"No permission to change nickname for {original_name}")
            except discord.HTTPException as e:
                logger.error(
                    f"HTTP error changing nickname for {original_name}: {str(e)}"
                )
        else:
            logger.info(
                f"Skipped nickname change for {original_name} (translation unchanged)"
            )

    except Exception as e:
        logger.error(f"Error processing new member {original_name}: {str(e)}")


@bot.command(name="translate_name")
@commands.has_permissions(manage_nicknames=True)
async def translate_name(
    ctx: commands.Context, member: Optional[discord.Member] = None, language: str = "ja"
):
    """
    Translate a member's name to Japanese or another language.

    If no member is specified, translates the command author's name.

    Args:
        ctx: The command context
        member: The member whose name should be translated (optional)
        language: Target language code (default: "ja" for Japanese)
    """
    await ctx.typing()  # Show typing indicator while processing
    target = member or ctx.author

    # Skip bots
    if target.bot:
        await ctx.send("I don't translate bot names.")
        return

    original_name = target.display_name

    # Send initial status message
    status_message = await ctx.send(f"Translating {original_name}'s name...")

    try:
        # Select the appropriate translation method based on language
        if language.lower() == "ja":
            translated_name = await Translate.to_japanese(original_name)
        else:
            translated_name = await Translate.translate_text(original_name, language)

        # Ensure the name complies with Discord's requirements
        if not translated_name or len(translated_name) > 32:
            if not translated_name:
                await status_message.edit(
                    content=f"Translation failed for {original_name}."
                )
                return
            # Truncate if too long
            if len(translated_name) > 32:
                logger.warning(f"Translated name too long: {translated_name}")
                translated_name = translated_name[:32]
                await status_message.edit(
                    content=f"The translated name was too long and has been truncated."
                )
                await asyncio.sleep(1)  # Brief pause before proceeding

        # Only proceed if the translation is different
        if translated_name == original_name:
            await status_message.edit(
                content=f"The translation for {original_name} is the same as the original name."
            )
            return

        try:
            await target.edit(nick=translated_name)
            await status_message.edit(
                content=f"Changed {original_name}'s nickname to {translated_name}"
            )
            logger.info(
                f"Manually changed {original_name}'s nickname to {translated_name}"
            )
        except discord.Forbidden:
            await status_message.edit(
                content=f"I don't have permission to change {original_name}'s nickname."
            )
            logger.warning(f"No permission to change nickname for {original_name}")
        except discord.HTTPException as e:
            await status_message.edit(content=f"Error changing nickname: {str(e)}")
            logger.error(f"HTTP error changing nickname: {str(e)}")

    except Exception as e:
        await status_message.edit(content=f"Error translating name: {str(e)}")
        logger.error(f"Error translating name: {str(e)}")


@bot.command(name="translate_all")
@commands.has_permissions(administrator=True)
async def translate_all(ctx: commands.Context, batch_size: int = 5, delay: float = 2.0):
    """
    Translate all members' names to Japanese in the server.

    This command requires administrator permissions.

    Args:
        ctx: The command context
        batch_size: Number of members to process in each batch (default: 5)
        delay: Delay in seconds between batches (default: 2.0)
    """
    status_message = await ctx.send("Starting to translate all member names...")
    success_count = 0
    fail_count = 0
    skip_count = 0

    # Filter out bots and members that already have nicknames
    members_to_process = [m for m in ctx.guild.members if not m.bot]
    total_members = len(members_to_process)

    await status_message.edit(
        content=f"Translating names for {total_members} members in batches of {batch_size}..."
    )

    # Process members in batches to avoid rate limits
    for i in range(0, total_members, batch_size):
        batch = members_to_process[i : i + batch_size]
        batch_results = await asyncio.gather(
            *[process_member_translation(member) for member in batch],
            return_exceptions=True,
        )

        # Count results
        for result in batch_results:
            if isinstance(result, Exception):
                fail_count += 1
                logger.error(f"Batch translation error: {str(result)}")
            elif result == "success":
                success_count += 1
            elif result == "skip":
                skip_count += 1
            else:
                fail_count += 1

        # Update status message periodically
        if (i + batch_size) % (batch_size * 5) == 0 or (
            i + batch_size
        ) >= total_members:
            await status_message.edit(
                content=(
                    f"Progress: {i + len(batch)}/{total_members} members processed. "
                    f"{success_count} successful, {fail_count} failed, {skip_count} skipped."
                )
            )

        # Add delay between batches to avoid rate limiting
        if i + batch_size < total_members:
            await asyncio.sleep(delay)

    await status_message.edit(
        content=(
            f"Finished translating names: {success_count} successful, "
            f"{fail_count} failed, {skip_count} skipped."
        )
    )
    logger.info(
        f"Bulk translate completed: {success_count} successful, {fail_count} failed, {skip_count} skipped."
    )


async def process_member_translation(member: discord.Member) -> str:
    """
    Helper function to process a single member's name translation.

    Args:
        member: The Discord member to process

    Returns:
        Status string: "success", "skip", or "fail"
    """
    original_name = member.display_name

    try:
        japanese_name = await Translate.to_japanese(original_name)

        # Skip if translation is the same or invalid
        if not japanese_name or japanese_name == original_name:
            logger.debug(f"Skipping {original_name} (no change in translation)")
            return "skip"

        # Truncate if too long for Discord
        if len(japanese_name) > 32:
            japanese_name = japanese_name[:32]

        # Apply the nickname
        try:
            await member.edit(nick=japanese_name)
            logger.info(
                f"Bulk translate: Changed {original_name}'s nickname to {japanese_name}"
            )
            return "success"
        except discord.Forbidden:
            logger.warning(f"Bulk translate: No permission for {original_name}")
            return "fail"
        except discord.HTTPException as e:
            logger.error(f"Bulk translate: HTTP error for {original_name}: {str(e)}")
            return "fail"

    except Exception as e:
        logger.error(f"Bulk translate: Error translating {original_name}: {str(e)}")
        return "fail"


@bot.command(name="reset_name")
@commands.has_permissions(manage_nicknames=True)
async def reset_name(ctx: commands.Context, member: Optional[discord.Member] = None):
    """
    Reset a member's nickname to their original username.

    Args:
        ctx: The command context
        member: The member whose nickname should be reset (optional)
    """
    target = member or ctx.author

    try:
        original_username = target.name  # This is the username, not the nickname
        current_nickname = target.nick

        if current_nickname is None:
            await ctx.send(f"{target.mention} doesn't have a nickname to reset.")
            return

        await target.edit(nick=None)  # Reset nickname
        await ctx.send(f"Reset {target.mention}'s nickname to their original username.")
        logger.info(f"Reset nickname for {current_nickname} to {original_username}")

    except discord.Forbidden:
        await ctx.send(f"I don't have permission to reset {target.mention}'s nickname.")
        logger.warning(f"No permission to reset nickname for {target}")
    except Exception as e:
        await ctx.send(f"Error resetting nickname: {str(e)}")
        logger.error(f"Error resetting nickname: {str(e)}")


@bot.event
async def on_command_error(ctx: commands.Context, error):
    """
    Handle command errors.

    Args:
        ctx: The command context
        error: The error that occurred
    """
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Member not found. Please mention a valid member.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"This command is on cooldown. Try again in {error.retry_after:.1f}s."
        )
    elif isinstance(error, commands.UserInputError):
        await ctx.send(f"Invalid input: {str(error)}")
    else:
        await ctx.send(f"An error occurred: {str(error)}")
        logger.error(f"Command error: {str(error)}")

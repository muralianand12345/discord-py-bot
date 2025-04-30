"""
Discord bot that translates usernames to Japanese using Groq LLM.
"""

import discord
import asyncio
from discord.ext import commands
from typing import Optional
import logging

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
        return

    original_name = member.display_name

    # Check if the name is already in Japanese
    from utils.translate import Translate

    if Translate.is_japanese(original_name):
        logger.info(f"Skipping translation for {original_name} (already Japanese)")
        return

    # Check if we have permission to change nicknames
    if not member.guild.me.guild_permissions.manage_nicknames:
        logger.warning(f"No permission to change nicknames in guild")
        return

    # Check if member is higher in hierarchy than the bot
    if member.top_role >= member.guild.me.top_role:
        logger.info(f"Cannot change nickname for {original_name} (higher role)")
        return

    try:
        japanese_name = await Translate.to_japanese(original_name)

        # Apply the nickname if we have a valid translation
        if japanese_name and japanese_name != original_name:
            # Truncate if too long
            if len(japanese_name) > 32:
                japanese_name = japanese_name[:32]

            try:
                await member.edit(nick=japanese_name)
                logger.info(f"Changed {original_name}'s nickname to {japanese_name}")
            except discord.Forbidden:
                logger.warning(f"No permission to change nickname for {original_name}")
            except discord.HTTPException as e:
                logger.error(f"HTTP error changing nickname: {str(e)}")
            except Exception as e:
                logger.error(f"Error changing nickname: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing new member {original_name}: {str(e)}")


@bot.command(name="translate_name")
@commands.has_permissions(manage_nicknames=True)
async def translate_name(
    ctx: commands.Context, member: Optional[discord.Member] = None, language: str = "ja"
):
    """
    Translate a member's name to Japanese or another language.

    Args:
        ctx: The command context
        member: The member whose name should be translated (optional)
        language: Target language code (default: "ja" for Japanese)
    """
    target = member or ctx.author

    # Skip bots
    if target.bot:
        await ctx.send("I don't translate bot names.")
        return

    original_name = target.display_name

    # Check if name is already in Japanese when translating to Japanese
    from utils.translate import Translate

    if language.lower() == "ja" and Translate.is_japanese(original_name):
        await ctx.send(f"{original_name}'s name is already in Japanese.")
        return

    # Check permissions
    if not ctx.guild.me.guild_permissions.manage_nicknames:
        await ctx.send("I don't have permission to manage nicknames in this server.")
        return

    # Check hierarchy
    if target.top_role >= ctx.guild.me.top_role:
        await ctx.send(
            f"I can't change {target.mention}'s nickname because their role is higher than mine."
        )
        return

    # Send initial status message
    status_message = await ctx.send(f"Translating {original_name}'s name...")

    try:
        # Select the appropriate translation method based on language
        if language.lower() == "ja":
            translated_name = await Translate.to_japanese(original_name)
        else:
            translated_name = await Translate.translate_text(original_name, language)

        # Truncate if too long
        if translated_name and len(translated_name) > 32:
            translated_name = translated_name[:32]
            await status_message.edit(
                content=f"The translated name was too long and has been truncated."
            )
            await asyncio.sleep(1)  # Brief pause

        # Only proceed if the translation is different
        if not translated_name or translated_name == original_name:
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
        except discord.HTTPException as e:
            await status_message.edit(content=f"Discord API error: {str(e)}")
        except Exception as e:
            await status_message.edit(content=f"Error changing nickname: {str(e)}")

    except Exception as e:
        await status_message.edit(content=f"Error translating name: {str(e)}")
        logger.error(f"Error translating name: {str(e)}")


@bot.command(name="translate_all")
@commands.has_permissions(administrator=True)
async def translate_all(ctx: commands.Context, batch_size: int = 5, delay: float = 2.0):
    """
    Translate all members' names to Japanese in the server.

    Args:
        ctx: The command context
        batch_size: Number of members to process in each batch (default: 5)
        delay: Delay in seconds between batches (default: 2.0)
    """
    status_message = await ctx.send("Starting to translate all member names...")
    success_count = 0
    fail_count = 0
    skip_count = 0

    # Filter out bots
    members_to_process = [m for m in ctx.guild.members if not m.bot]
    total_members = len(members_to_process)

    await status_message.edit(
        content=f"Translating names for {total_members} members..."
    )

    # Process members in batches to avoid rate limits
    for i in range(0, total_members, batch_size):
        batch = members_to_process[i : i + batch_size]

        for member in batch:
            try:
                original_name = member.display_name

                # Skip members without permission to change nickname
                if not ctx.guild.me.guild_permissions.manage_nicknames:
                    logger.warning(f"No permission to change nicknames in guild")
                    fail_count += 1
                    continue

                # Skip if member is above bot in hierarchy
                if member.top_role >= ctx.guild.me.top_role:
                    logger.info(f"Skipping {original_name} (higher role than bot)")
                    skip_count += 1
                    continue

                # Check if name is already Japanese
                from utils.translate import Translate

                if Translate.is_japanese(original_name):
                    logger.info(f"Skipping {original_name} (already Japanese)")
                    skip_count += 1
                    continue

                # Translate the name
                japanese_name = await Translate.to_japanese(original_name)

                # Skip if translation is the same or failed
                if not japanese_name or japanese_name == original_name:
                    logger.info(f"Skipping {original_name} (no change in translation)")
                    skip_count += 1
                    continue

                # Truncate if too long
                if len(japanese_name) > 32:
                    japanese_name = japanese_name[:32]

                # Apply the nickname
                await member.edit(nick=japanese_name)
                success_count += 1
                logger.info(f"Batch translate: {original_name} → {japanese_name}")

            except discord.Forbidden:
                logger.warning(
                    f"Forbidden to change nickname for {member.display_name}"
                )
                fail_count += 1
            except discord.HTTPException as e:
                logger.error(f"HTTP error for {member.display_name}: {e}")
                fail_count += 1
            except Exception as e:
                logger.error(f"Error processing {member.display_name}: {str(e)}")
                fail_count += 1

        # Update status message
        if (i + batch_size) % (batch_size * 5) == 0 or (
            i + batch_size
        ) >= total_members:
            await status_message.edit(
                content=(
                    f"Progress: {i + len(batch)}/{total_members} members processed. "
                    f"{success_count} successful, {fail_count} failed, {skip_count} skipped."
                )
            )

        # Add delay between batches
        if i + batch_size < total_members:
            await asyncio.sleep(delay)

    await status_message.edit(
        content=(
            f"Finished translating names: {success_count} successful, "
            f"{fail_count} failed, {skip_count} skipped."
        )
    )


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
        current_nickname = target.nick

        if current_nickname is None:
            await ctx.send(f"{target.mention} doesn't have a nickname to reset.")
            return

        await target.edit(nick=None)  # Reset nickname
        await ctx.send(f"Reset {target.mention}'s nickname to their original username.")

    except discord.Forbidden:
        await ctx.send(f"I don't have permission to reset {target.mention}'s nickname.")
    except Exception as e:
        await ctx.send(f"Error resetting nickname: {str(e)}")


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

"""
Nickname management cog for Discord bot.
Contains the original name translation functionality.
"""

import discord
import asyncio
import logging
from typing import Optional
from discord.ext import commands

from utils.translate import Translate
from utils.settings import FEATURES, COOLDOWNS


class NicknameCog(commands.Cog, name="Nickname"):
    """Commands for managing and translating nicknames."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger("nickname_cog")
        self.auto_translation_enabled = FEATURES.get("auto_translation", True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle new member joining by translating their display name to Japanese."""
        # Skip if feature is disabled
        if not self.auto_translation_enabled:
            return

        # Skip bots
        if member.bot:
            return

        original_name = member.display_name

        # Check if the name is already in Japanese
        if Translate.is_japanese(original_name):
            self.logger.info(
                f"Skipping translation for {original_name} (already Japanese)"
            )
            return

        # Check if we have permission to change nicknames
        if not member.guild.me.guild_permissions.manage_nicknames:
            self.logger.warning(f"No permission to change nicknames in guild")
            return

        # Check if member is higher in hierarchy than the bot
        if member.top_role >= member.guild.me.top_role:
            self.logger.info(
                f"Cannot change nickname for {original_name} (higher role)"
            )
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
                    self.logger.info(
                        f"Changed {original_name}'s nickname to {japanese_name}"
                    )
                except discord.Forbidden:
                    self.logger.warning(
                        f"No permission to change nickname for {original_name}"
                    )
                except discord.HTTPException as e:
                    self.logger.error(f"HTTP error changing nickname: {str(e)}")
                except Exception as e:
                    self.logger.error(f"Error changing nickname: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error processing new member {original_name}: {str(e)}")

    @commands.command(name="translate_name", aliases=["tn"])
    @commands.guild_only()
    @commands.has_permissions(manage_nicknames=True)
    @commands.cooldown(1, COOLDOWNS.get("translation", 5), commands.BucketType.user)
    async def translate_name(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None,
        language: str = "ja",
    ):
        """
        Translate a member's name to another language.

        Args:
            member: The member whose name should be translated (defaults to you)
            language: Target language code (default: "ja" for Japanese)

        Examples:
            !translate_name @user
            !translate_name @user fr
            !tn @user es
        """
        target = member or ctx.author

        # Skip bots
        if target.bot:
            await ctx.send("I don't translate bot names.")
            return

        original_name = target.display_name

        # Check if name is already in Japanese when translating to Japanese
        if language.lower() == "ja" and Translate.is_japanese(original_name):
            await ctx.send(f"{original_name}'s name is already in Japanese.")
            return

        # Check permissions
        if not ctx.guild.me.guild_permissions.manage_nicknames:
            await ctx.send(
                "I don't have permission to manage nicknames in this server."
            )
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
                translated_name = await Translate.translate_text(
                    original_name, language
                )

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
                self.logger.info(
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
            self.logger.error(f"Error translating name: {str(e)}")

    @commands.command(name="translate_all", aliases=["tall"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(
        1, COOLDOWNS.get("batch_operations", 30), commands.BucketType.guild
    )
    async def translate_all(
        self, ctx: commands.Context, batch_size: int = 5, delay: float = 2.0
    ):
        """
        Translate all members' names to Japanese in the server.

        Args:
            batch_size: Number of members to process in each batch (default: 5)
            delay: Delay in seconds between batches (default: 2.0)

        Example:
            !translate_all 10 1.5
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
                        self.logger.warning(
                            f"No permission to change nicknames in guild"
                        )
                        fail_count += 1
                        continue

                    # Skip if member is above bot in hierarchy
                    if member.top_role >= ctx.guild.me.top_role:
                        self.logger.info(
                            f"Skipping {original_name} (higher role than bot)"
                        )
                        skip_count += 1
                        continue

                    # Check if name is already Japanese
                    if Translate.is_japanese(original_name):
                        self.logger.info(f"Skipping {original_name} (already Japanese)")
                        skip_count += 1
                        continue

                    # Translate the name
                    japanese_name = await Translate.to_japanese(original_name)

                    # Skip if translation is the same or failed
                    if not japanese_name or japanese_name == original_name:
                        self.logger.info(
                            f"Skipping {original_name} (no change in translation)"
                        )
                        skip_count += 1
                        continue

                    # Truncate if too long
                    if len(japanese_name) > 32:
                        japanese_name = japanese_name[:32]

                    # Apply the nickname
                    await member.edit(nick=japanese_name)
                    success_count += 1
                    self.logger.info(
                        f"Batch translate: {original_name} → {japanese_name}"
                    )

                except discord.Forbidden:
                    self.logger.warning(
                        f"Forbidden to change nickname for {member.display_name}"
                    )
                    fail_count += 1
                except discord.HTTPException as e:
                    self.logger.error(f"HTTP error for {member.display_name}: {e}")
                    fail_count += 1
                except Exception as e:
                    self.logger.error(
                        f"Error processing {member.display_name}: {str(e)}"
                    )
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

    @commands.command(name="reset_name", aliases=["rn"])
    @commands.guild_only()
    @commands.has_permissions(manage_nicknames=True)
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def reset_name(
        self, ctx: commands.Context, member: Optional[discord.Member] = None
    ):
        """
        Reset a member's nickname to their original username.

        Args:
            member: The member whose nickname should be reset (defaults to you)

        Example:
            !reset_name @user
            !rn @user
        """
        target = member or ctx.author

        try:
            current_nickname = target.nick

            if current_nickname is None:
                await ctx.send(f"{target.mention} doesn't have a nickname to reset.")
                return

            await target.edit(nick=None)  # Reset nickname
            await ctx.send(
                f"Reset {target.mention}'s nickname to their original username."
            )
            self.logger.info(f"Reset nickname for {target.name}")

        except discord.Forbidden:
            await ctx.send(
                f"I don't have permission to reset {target.mention}'s nickname."
            )
        except Exception as e:
            await ctx.send(f"Error resetting nickname: {str(e)}")
            self.logger.error(f"Error resetting nickname: {str(e)}")

    @commands.command(name="random_name", aliases=["rname"])
    @commands.guild_only()
    @commands.has_permissions(manage_nicknames=True)
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def random_name(
        self, ctx: commands.Context, member: Optional[discord.Member] = None
    ):
        """
        Give a member a random Japanese name.

        Args:
            member: The member to give a random name (defaults to you)

        Example:
            !random_name @user
            !rname
        """
        # This is a new command that wasn't in the original code
        target = member or ctx.author

        # Skip bots
        if target.bot:
            await ctx.send("I don't change bot names.")
            return

        # Check permissions
        if not ctx.guild.me.guild_permissions.manage_nicknames:
            await ctx.send(
                "I don't have permission to manage nicknames in this server."
            )
            return

        # Check hierarchy
        if target.top_role >= ctx.guild.me.top_role:
            await ctx.send(
                f"I can't change {target.mention}'s nickname because their role is higher than mine."
            )
            return

        # Send initial status message
        status_message = await ctx.send(f"Generating a random Japanese name...")

        try:
            import random

            # List of common Japanese first names
            first_names = [
                "Haruto",
                "Yuki",
                "Sora",
                "Haruka",
                "Kohaku",
                "Ren",
                "Aoi",
                "Hana",
                "Yui",
                "Kaito",
                "Mei",
                "Takumi",
                "Akira",
                "Rin",
            ]

            # List of common Japanese last names
            last_names = [
                "Sato",
                "Suzuki",
                "Takahashi",
                "Tanaka",
                "Watanabe",
                "Ito",
                "Yamamoto",
                "Nakamura",
                "Kobayashi",
                "Kato",
            ]

            # Generate random name
            random_name = f"{random.choice(last_names)} {random.choice(first_names)}"

            # Translate to Japanese
            japanese_name = await Translate.to_japanese(random_name)

            # Apply the nickname
            await target.edit(nick=japanese_name)
            await status_message.edit(
                content=f"Changed {target.mention}'s nickname to {japanese_name}"
            )
            self.logger.info(
                f"Set random Japanese name for {target.name}: {japanese_name}"
            )

        except Exception as e:
            await status_message.edit(content=f"Error setting random name: {str(e)}")
            self.logger.error(f"Error setting random name: {str(e)}")

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        """Handle errors for this cog's commands."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"This command is on cooldown. Try again in {error.retry_after:.1f}s."
            )
            return

        # Let the global error handler deal with other errors
        if ctx.command and ctx.command.cog_name == self.__class__.__name__:
            self.logger.error(f"Error in {ctx.command.name}: {str(error)}")


async def setup(bot: commands.Bot):
    """Add this cog to the bot."""
    await bot.add_cog(NicknameCog(bot))

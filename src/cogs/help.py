"""
Custom help command implementation for the bot.
"""

import logging
import discord
from discord.ext import commands
from typing import Optional, Dict, List, Mapping, Union

from utils.settings import BOT_PREFIX


class CustomHelpCommand(commands.HelpCommand):
    """Custom implementation of the help command."""

    def __init__(self, **options):
        super().__init__(
            command_attrs={
                "cooldown": commands.CooldownMapping.from_cooldown(
                    1, 3.0, commands.BucketType.user
                ),
                "help": "Shows help for commands and categories",
            },
            **options,
        )

    async def send_bot_help(
        self, mapping: Mapping[Optional[commands.Cog], List[commands.Command]]
    ):
        """Handle the default help command."""
        embed = discord.Embed(
            title="Bot Commands",
            description=f"Use `{BOT_PREFIX}help [command]` for more info on a command.\n"
            f"Use `{BOT_PREFIX}help [category]` for more info on a category.",
            color=discord.Color.blue(),
        )

        # Filter out hidden commands and organize by cog
        for cog, cmds in mapping.items():
            if cog and cmds:
                # Filter out hidden commands
                filtered_cmds = [cmd for cmd in cmds if not cmd.hidden]
                if filtered_cmds:
                    cog_name = getattr(cog, "qualified_name", "No Category")
                    # Get the first 5 commands as examples
                    command_list = ", ".join(
                        f"`{cmd.name}`" for cmd in filtered_cmds[:5]
                    )
                    if len(filtered_cmds) > 5:
                        command_list += f" and {len(filtered_cmds) - 5} more"
                    embed.add_field(name=cog_name, value=command_list, inline=False)

        # Add a note about the bot
        embed.set_footer(text=f"Type {BOT_PREFIX}about for more information")

        # Send the help embed
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog):
        """Send help for a specific cog."""
        embed = discord.Embed(
            title=f"{cog.qualified_name} Commands",
            description=cog.description or "No description provided.",
            color=discord.Color.blue(),
        )

        # Add commands from this cog
        filtered_cmds = [cmd for cmd in cog.get_commands() if not cmd.hidden]
        if filtered_cmds:
            for cmd in filtered_cmds:
                signature = self.get_command_signature(cmd)
                # Truncate command description if it's too long
                description = cmd.help or "No description provided."
                if len(description) > 100:
                    description = description[:97] + "..."
                embed.add_field(name=signature, value=description, inline=False)
        else:
            embed.add_field(
                name="No Commands",
                value="This category has no commands available to you.",
            )

        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command: commands.Command):
        """Send help for a specific command."""
        embed = discord.Embed(
            title=self.get_command_signature(command),
            description=command.help or "No description provided.",
            color=discord.Color.blue(),
        )

        # Show command aliases if they exist
        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{alias}`" for alias in command.aliases),
                inline=False,
            )

        # Show cooldown if applicable
        if command._buckets and command._buckets._cooldown:
            embed.add_field(
                name="Cooldown",
                value=f"{command._buckets._cooldown.rate} use(s) every {command._buckets._cooldown.per:.0f} seconds",
                inline=False,
            )

        # Show command usage if available
        if command.usage:
            embed.add_field(name="Usage", value=command.usage, inline=False)

        # Show subcommands for group commands
        if isinstance(command, commands.Group):
            subcommand_list = "\n".join(
                f"`{self.context.clean_prefix}{command.name} {subcommand.name}` - {subcommand.short_doc or 'No description'}"
                for subcommand in command.commands
            )
            if subcommand_list:
                embed.add_field(name="Subcommands", value=subcommand_list, inline=False)

        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group: commands.Group):
        """Send help for a command group."""
        embed = discord.Embed(
            title=self.get_command_signature(group),
            description=group.help or "No description provided.",
            color=discord.Color.blue(),
        )

        # Add the main command info
        if group.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{alias}`" for alias in group.aliases),
                inline=False,
            )

        # Show command usage if available
        if group.usage:
            embed.add_field(name="Usage", value=group.usage, inline=False)

        # Show subcommands
        filtered_commands = await self.filter_commands(group.commands, sort=True)
        if filtered_commands:
            for command in filtered_commands:
                signature = f"{command.name} {command.signature}"
                help_text = command.short_doc or "No description"
                embed.add_field(name=signature, value=help_text, inline=False)
        else:
            embed.add_field(
                name="No Subcommands",
                value="This command group has no subcommands available to you.",
            )

        await self.get_destination().send(embed=embed)

    async def send_error_message(self, error: str):
        """Send error message when command or cog is not found."""
        embed = discord.Embed(
            title="Error", description=error, color=discord.Color.red()
        )
        await self.get_destination().send(embed=embed)


class HelpCog(commands.Cog, name="Help"):
    """Help command and documentation."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger("help_cog")

        # Store the original help command so we can restore it when needed
        self._original_help_command = bot.help_command

        # Create and set our custom help command
        # Don't pass self directly to avoid circular reference
        bot.help_command = CustomHelpCommand()
        # Set the cog after creation to avoid pickling issues
        bot.help_command.cog = self

    def cog_unload(self):
        """Restore the original help command when the cog is unloaded."""
        self.bot.help_command = self._original_help_command

    @commands.command(name="about")
    async def about(self, ctx: commands.Context):
        """Show information about this bot."""
        embed = discord.Embed(
            title=f"About {self.bot.user.name}",
            description="A multi-purpose Discord bot with modular commands and features.",
            color=discord.Color.blue(),
        )

        # Add bot information
        embed.add_field(
            name="Features",
            value=(
                "• Nickname translation to Japanese\n"
                "• Server moderation and management\n"
                "• Utility commands\n"
                "• Fun commands\n"
                "• Customizable message filtering"
            ),
            inline=False,
        )

        # Add usage information
        embed.add_field(
            name="Usage",
            value=f"Type `{BOT_PREFIX}help` to see all available commands.",
            inline=False,
        )

        # Add credits
        embed.add_field(
            name="Credits",
            value=("Created by Murali Anand\n" "Licensed under MIT License"),
            inline=False,
        )

        # Add GitHub link
        embed.add_field(
            name="GitHub",
            value="[Source code](https://github.com/muralianand12345/discord-name-changer)",
            inline=False,
        )

        # Add bot avatar if available
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Add this cog to the bot."""
    await bot.add_cog(HelpCog(bot))

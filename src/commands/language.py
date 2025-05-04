import discord
from discord.ext import commands

from bot import bot, logger
from utils.translator import Translator


@bot.command(name="language")
@commands.has_permissions(manage_guild=True)
async def language(ctx, new_language: str = None):
    """
    Check or change the default translation language for the bot.

    Usage:
        !language - Show current language
        !language [language] - Set new default language

    Examples:
        !language
        !language Spanish
        !language Japanese
    """
    if new_language:
        # Set the new default language
        await Translator.set_translation_language(new_language)

        # Create an embed to show the update
        embed = discord.Embed(
            title="Language Updated",
            description=f"Default translation language set to: **{new_language}**",
            color=0x00FF00,  # Green
        )

        embed.add_field(
            name="Effects",
            value=(
                "• This language will be used for all name translations\n"
                "• Welcome messages will use this language for name translations\n"
                "• This setting persists across bot restarts"
            ),
            inline=False,
        )

        embed.set_footer(
            text=f"Changed by {ctx.author.name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None,
        )

        await ctx.send(embed=embed)
        logger.info(f"Default language changed to {new_language} by {ctx.author.name}")
    else:
        # Show the current language
        current_language = await Translator.get_translation_language()

        embed = discord.Embed(
            title="Current Translation Language",
            description=f"The bot is currently set to translate names to: **{current_language}**",
            color=0x5CDBF0,  # Light blue
        )

        embed.add_field(
            name="Change Language",
            value=f"Use `{ctx.prefix}language [language]` to change the default language.",
            inline=False,
        )

        embed.add_field(
            name="Examples",
            value=(
                f"`{ctx.prefix}language Arabic`\n"
                f"`{ctx.prefix}language Spanish`\n"
                f"`{ctx.prefix}language Japanese`"
            ),
            inline=False,
        )

        await ctx.send(embed=embed)


@language.error
async def language_error(ctx, error):
    """Error handler for the language command."""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "You need the 'Manage Server' permission to change the default language."
        )
    else:
        await ctx.send(f"An error occurred: {str(error)}")
        logger.error(f"Error in language command: {str(error)}")

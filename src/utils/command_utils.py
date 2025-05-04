import discord
from discord.ext import commands

from bot import bot, logger


def register_commands_help() -> None:
    """Register help information for all commands."""

    # Nickname command help
    bot.get_command(
        "nickname"
    ).help = """
    Change or reset display names of users.
    
    Usage:
        !nickname user @user1 @user2 [language=Language]
        !nickname role "Role Name" [language=Language]
        !nickname all [language=Language]
        !nickname reset @user1 @user2
        !nickname reset-role "Role Name"
        !nickname reset-all
    
    Examples:
        !nickname user @alex @jamie language=Spanish
        !nickname role "New Members" language=Japanese
        !nickname all language=Arabic
        !nickname reset @user1 @user2
    """

    # Language command help
    bot.get_command(
        "language"
    ).help = """
    Check or change the default translation language for the bot.
    
    Usage:
        !language - Show current language
        !language [language] - Set new default language
        
    Examples:
        !language
        !language Spanish
        !language Japanese
    
    Note: This setting persists across bot restarts and affects welcome messages.
    """


async def check_command_permissions(
    ctx: commands.Context, permission_name: str
) -> bool:
    """
    Check if a user has the required permissions to run a command.

    Args:
        ctx: Command context
        permission_name: Name of the permission to check

    Returns:
        True if user has permission, False otherwise
    """
    # Always allow server owner
    if ctx.guild and ctx.author.id == ctx.guild.owner_id:
        return True

    # Check for specific permission
    required_permission = getattr(discord.Permissions, permission_name, None)
    if required_permission is None:
        logger.error(f"Invalid permission name: {permission_name}")
        return False

    # Check if user has the permission
    return getattr(ctx.author.guild_permissions, permission_name, False)


def setup_commands():
    """
    Set up commands and their metadata after bot initialization.
    This should be called after the bot has loaded all commands.
    """
    try:
        # Register help text for commands
        register_commands_help()

        logger.info("Command utilities set up successfully")
    except Exception as e:
        logger.error(f"Error setting up command utilities: {str(e)}")

import asyncio
import discord
from discord.ext import commands
from typing import Optional, Tuple

from bot import bot, logger
from utils.translator import Translator


@bot.command(name="nickname")
@commands.has_permissions(manage_nicknames=True)
async def nickname(ctx, mode: str = None, *, args: str = None):
    """
    Change display names of users to translated names.

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
    if not mode:
        # Show help if no mode provided
        help_embed = discord.Embed(
            title="Nickname Command Help",
            description="Translate user display names to various languages",
            color=0x5CDBF0,
        )

        help_embed.add_field(
            name="User Mode",
            value="Change nicknames for mentioned users\n`!nickname user @user1 @user2 [language=Language]`",
            inline=False,
        )

        help_embed.add_field(
            name="Role Mode",
            value='Change nicknames for all users with a specific role\n`!nickname role "Role Name" [language=Language]`',
            inline=False,
        )

        help_embed.add_field(
            name="All Mode",
            value="Change nicknames for all server members\n`!nickname all [language=Language]`",
            inline=False,
        )

        help_embed.add_field(
            name="Reset Mode",
            value="Remove nicknames for mentioned users\n`!nickname reset @user1 @user2`",
            inline=False,
        )

        help_embed.add_field(
            name="Reset Role Mode",
            value='Remove nicknames for all users with a specific role\n`!nickname reset-role "Role Name"`',
            inline=False,
        )

        help_embed.add_field(
            name="Reset All Mode",
            value="Remove nicknames for all server members\n`!nickname reset-all`",
            inline=False,
        )

        help_embed.set_footer(
            text="Default language: " + await Translator.get_translation_language()
        )

        await ctx.send(embed=help_embed)
        return

    # Process based on the mode
    mode = mode.lower()

    # Handle user mode
    if mode == "user":
        await process_user_mode(ctx, args)

    # Handle role mode
    elif mode == "role":
        await process_role_mode(ctx, args)

    # Handle all mode
    elif mode == "all":
        await process_all_mode(ctx, args)

    # Handle reset mode
    elif mode == "reset":
        await process_reset_mode(ctx, args)

    # Handle reset-role mode
    elif mode == "reset-role":
        await process_reset_role_mode(ctx, args)

    # Handle reset-all mode
    elif mode == "reset-all":
        await process_reset_all_mode(ctx)

    # Unknown mode
    else:
        await ctx.send(
            f"Unknown mode: `{mode}`. Use `user`, `role`, `all`, `reset`, `reset-role`, or `reset-all`."
        )


async def process_user_mode(ctx, args):
    """Process nickname command in user mode."""
    if not args:
        await ctx.send("Please mention at least one user to change their nickname.")
        return

    # Parse arguments and extract language
    language = await extract_language(args)

    # Set as new default language
    await Translator.set_translation_language(language)

    # Get mentioned users
    mentioned_users = ctx.message.mentions

    if not mentioned_users:
        await ctx.send("Please mention at least one user to change their nickname.")
        return

    # Process the mentioned users
    results = []
    for user in mentioned_users:
        result = await translate_user_nickname(ctx, user, language)
        results.append(result)

    # Create and send results embed
    await send_results_embed(ctx, results, f"User Mode ({language})")


async def process_role_mode(ctx, args):
    """Process nickname command in role mode."""
    if not args:
        await ctx.send('Please specify a role name, e.g., `!nickname role "Member"`')
        return

    # Parse arguments and extract language
    language = await extract_language(args)

    # Set as new default language
    await Translator.set_translation_language(language)

    # Extract role name
    role_name = extract_quoted_text(args)
    if not role_name:
        # Try to get everything before "language=" if present
        if "language=" in args:
            role_name = args.split("language=")[0].strip()
        else:
            role_name = args.strip()

    # Find the role
    role = discord.utils.get(ctx.guild.roles, name=role_name)

    if not role:
        await ctx.send(f"Role '{role_name}' not found.")
        return

    # Get members with the role
    members = [member for member in role.members if not member.bot]

    if not members:
        await ctx.send(f"No members found with the role '{role_name}'.")
        return

    # Send initial response
    response = await ctx.send(
        f"🔄 Processing {len(members)} members with role '{role_name}'..."
    )

    # Process members in chunks to avoid rate limits
    await process_members_in_chunks(
        ctx, members, language, f"Role: {role_name}", response, is_reset=False
    )


async def process_all_mode(ctx, args):
    """Process nickname command in all mode."""
    # Extract language if provided
    language = await extract_language(args or "")

    # Set as new default language
    await Translator.set_translation_language(language)

    # Get all non-bot members
    members = [member for member in ctx.guild.members if not member.bot]

    if not members:
        await ctx.send("No members found in the server.")
        return

    # Send initial response
    response = await ctx.send(
        f"🔄 Processing all {len(members)} members in the server..."
    )

    # Process members in chunks to avoid rate limits
    await process_members_in_chunks(
        ctx, members, language, "All Members", response, is_reset=False
    )


async def process_reset_mode(ctx, args):
    """Process nickname command in reset mode."""
    if not args:
        await ctx.send("Please mention at least one user to reset their nickname.")
        return

    # Get mentioned users
    mentioned_users = ctx.message.mentions

    if not mentioned_users:
        await ctx.send("Please mention at least one user to reset their nickname.")
        return

    # Process the mentioned users
    results = []
    for user in mentioned_users:
        result = await reset_user_nickname(ctx, user)
        results.append(result)

    # Create and send results embed
    await send_results_embed(ctx, results, "Reset Nicknames")


async def process_reset_role_mode(ctx, args):
    """Process nickname command in reset-role mode."""
    if not args:
        await ctx.send(
            'Please specify a role name, e.g., `!nickname reset-role "Member"`'
        )
        return

    # Extract role name
    role_name = extract_quoted_text(args)
    if not role_name:
        role_name = args.strip()

    # Find the role
    role = discord.utils.get(ctx.guild.roles, name=role_name)

    if not role:
        await ctx.send(f"Role '{role_name}' not found.")
        return

    # Get members with the role
    members = [member for member in role.members if not member.bot]

    if not members:
        await ctx.send(f"No members found with the role '{role_name}'.")
        return

    # Send initial response
    response = await ctx.send(
        f"🔄 Resetting nicknames for {len(members)} members with role '{role_name}'..."
    )

    # Process members in chunks to avoid rate limits
    await process_members_in_chunks(
        ctx, members, None, f"Role: {role_name}", response, is_reset=True
    )


async def process_reset_all_mode(ctx):
    """Process nickname command in reset-all mode."""
    # Get all non-bot members
    members = [member for member in ctx.guild.members if not member.bot]

    if not members:
        await ctx.send("No members found in the server.")
        return

    # Send initial response
    response = await ctx.send(
        f"🔄 Resetting nicknames for all {len(members)} members in the server..."
    )

    # Process members in chunks to avoid rate limits
    await process_members_in_chunks(
        ctx, members, None, "All Members", response, is_reset=True
    )


async def process_members_in_chunks(
    ctx, members, language, description, initial_message, is_reset=False
):
    """Process a large number of members in chunks to avoid rate limits."""
    # Create progress embed
    operation_type = "Reset" if is_reset else f"Translation ({language})"
    embed = discord.Embed(
        title=f"Nickname {operation_type}",
        description=f"Processing {len(members)} {description}...",
        color=0x5CDBF0,
    )
    embed.add_field(name="Status", value="Starting...", inline=False)
    status_message = await ctx.send(embed=embed)

    # Process members in chunks
    chunk_size = 5
    total_members = len(members)
    results = []
    successful = 0
    skipped = 0
    failed = 0

    for i in range(0, total_members, chunk_size):
        chunk = members[i : i + chunk_size]
        chunk_results = []

        for member in chunk:
            if is_reset:
                result = await reset_user_nickname(ctx, member)
            else:
                result = await translate_user_nickname(ctx, member, language)

            chunk_results.append(result)

            # Update counters
            if "Changed" in result[0] or "Reset" in result[0]:
                successful += 1
            elif "Cannot modify" in result[0] or "No" in result[0]:
                skipped += 1
            else:
                failed += 1

        results.extend(chunk_results)

        # Update progress
        progress = min(100, int((i + len(chunk)) / total_members * 100))

        embed = discord.Embed(
            title=f"Nickname {operation_type}",
            description=f"Processing {total_members} {description}...",
            color=0x5CDBF0,
        )
        embed.add_field(
            name="Progress",
            value=f"{progress}% complete ({i + len(chunk)}/{total_members})",
            inline=False,
        )
        embed.add_field(
            name="Status",
            value=f"✅ Success: {successful}\n⏭️ Skipped: {skipped}\n❌ Failed: {failed}",
            inline=False,
        )

        await status_message.edit(embed=embed)

        # Short delay to avoid rate limits
        await asyncio.sleep(1)

    # Create final results embed
    final_embed = discord.Embed(
        title=f"Nickname {operation_type} Complete",
        description=f"Processed {total_members} {description}"
        + (f" with language: {language}" if not is_reset else ""),
        color=0x00FF00,
    )

    final_embed.add_field(
        name="Results Summary",
        value=f"✅ Success: {successful}\n⏭️ Skipped: {skipped}\n❌ Failed: {failed}",
        inline=False,
    )

    # Add detailed results (limited to avoid hitting Discord character limits)
    if results:
        # Only include the first 15 results to avoid message size limits
        detailed_results = "\n".join([result[0] for result in results[:15]])
        if len(results) > 15:
            detailed_results += f"\n... and {len(results) - 15} more"

        final_embed.add_field(
            name="Detailed Results", value=detailed_results, inline=False
        )

    # Add footer
    final_embed.set_footer(
        text=f"Requested by {ctx.author.name}",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else None,
    )

    await status_message.edit(embed=final_embed)
    await initial_message.delete()


async def translate_user_nickname(
    ctx, user: discord.Member, language: str
) -> Tuple[str, str]:
    """
    Translate a user's display name to the specified language.

    Args:
        ctx: Command context
        user: User to translate display name for
        language: Target language for translation

    Returns:
        Tuple containing (result_message, status)
    """
    # Skip if we can't modify the user due to role hierarchy
    if (
        not ctx.guild.me.top_role > user.top_role
        and ctx.guild.owner_id != ctx.author.id
    ):
        return (f"• Cannot modify {user.display_name} (higher role)", "skipped")

    # Get user's current display name or username if no nickname is set
    current_name = user.display_name

    # Translate the display name
    translated_name = await Translator.translate_name(current_name, language)

    # Skip if no change needed
    if translated_name == current_name:
        return (f"• No translation needed for {current_name}", "skipped")

    # Try to set the nickname
    try:
        await user.edit(nick=translated_name)
        logger.info(
            f"Changed nickname for {user.name} from {current_name} to {translated_name}"
        )
        return (f"• Changed {current_name} → {translated_name}", "success")
    except discord.Forbidden:
        return (f"• Missing permissions to change {current_name}'s nickname", "failed")
    except Exception as e:
        logger.error(f"Failed to set nickname for {current_name}: {str(e)}")
        return (f"• Error changing {current_name}'s nickname: {str(e)}", "failed")


async def reset_user_nickname(ctx, user: discord.Member) -> Tuple[str, str]:
    """
    Reset a user's nickname to their default username.

    Args:
        ctx: Command context
        user: User to reset nickname for

    Returns:
        Tuple containing (result_message, status)
    """
    # Skip if we can't modify the user due to role hierarchy
    if (
        not ctx.guild.me.top_role > user.top_role
        and ctx.guild.owner_id != ctx.author.id
    ):
        return (f"• Cannot modify {user.display_name} (higher role)", "skipped")

    # Check if user already has their default name
    if user.nick is None:
        return (f"• No nickname to reset for {user.name}", "skipped")

    # Store current nickname for logging
    current_nickname = user.nick

    # Try to reset the nickname
    try:
        await user.edit(nick=None)
        logger.info(
            f"Reset nickname for {user.name} from {current_nickname} to default"
        )
        return (f"• Reset {current_nickname} → {user.name}", "success")
    except discord.Forbidden:
        return (
            f"• Missing permissions to reset {user.display_name}'s nickname",
            "failed",
        )
    except Exception as e:
        logger.error(f"Failed to reset nickname for {user.display_name}: {str(e)}")
        return (f"• Error resetting {user.display_name}'s nickname: {str(e)}", "failed")


async def send_results_embed(ctx, results, title):
    """Send an embed with the results of the nickname changes."""
    embed = discord.Embed(
        title=title,
        description="\n".join([result[0] for result in results]),
        color=0x5CDBF0,
    )

    # Add footer
    embed.set_footer(
        text=f"Requested by {ctx.author.name}",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else None,
    )

    await ctx.send(embed=embed)


async def extract_language(args: str) -> str:
    """
    Extract language parameter from command arguments.

    Args:
        args: Command arguments string

    Returns:
        Language string or default language
    """
    if not args:
        return await Translator.get_translation_language()

    # Check for language parameter
    if "language=" in args:
        parts = args.split()
        for part in parts:
            if part.startswith("language="):
                return part.split("=")[1].strip()

    # Return default language if not specified
    return await Translator.get_translation_language()


def extract_quoted_text(text: str) -> Optional[str]:
    """
    Extract text within quotes from a string.

    Args:
        text: String to extract quoted text from

    Returns:
        Quoted text or None if no quotes found
    """
    if '"' in text:
        start = text.find('"')
        end = text.find('"', start + 1)
        if start != -1 and end != -1:
            return text[start + 1 : end]
    return None


@nickname.error
async def nickname_error(ctx, error):
    """Error handler for the nickname command."""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "You need the 'Manage Nicknames' permission to use this command."
        )
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("I don't have the necessary permissions to change nicknames.")
    else:
        await ctx.send(f"An error occurred: {str(error)}")
        logger.error(f"Error in nickname command: {str(error)}")

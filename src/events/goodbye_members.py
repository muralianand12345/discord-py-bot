import discord
import random


from bot import bot, logger
from config import BOT, LLM
from utils.llm import LLMClient, LLMMessage
from utils.translator import Translator


@bot.event
async def on_member_remove(member):
    """Event handler for when a member leaves the server."""
    # Skip if not in the configured guild
    if bot.guild_id and member.guild.id != bot.guild_id:
        return

    # Log the member leaving
    logger.info(f"Member left: {member.name}#{member.discriminator} (ID: {member.id})")

    # Send goodbye message if goodbye channel is configured
    if BOT.GOODBYE.GOODBYE_CHANNEL_ID:
        try:
            channel = member.guild.get_channel(int(BOT.GOODBYE.GOODBYE_CHANNEL_ID))
            if channel:
                # Create and send goodbye embed
                embed = await create_goodbye_embed(member)
                await channel.send(embed=embed)
            else:
                logger.warning(
                    f"Goodbye channel with ID {BOT.GOODBYE.GOODBYE_CHANNEL_ID} not found"
                )
        except Exception as e:
            logger.error(f"Failed to send goodbye message for {member.name}: {str(e)}")


async def create_goodbye_embed(member):
    """Creates a custom goodbye embed for the departing member."""
    # Get current language from persistent settings
    language = await Translator.get_translation_language()

    embed = discord.Embed(
        title=f"Goodbye! 👋",
        description=await generate_goodbye_message(member, language),
        color=0xED4245,  # Soft red color
    )

    # Add member info
    embed.add_field(name="Member", value=f"{member.name}", inline=True)
    embed.add_field(
        name="Joined Server",
        value=f"<t:{int(member.joined_at.timestamp()) if member.joined_at else 0}:R>",
        inline=True,
    )
    embed.add_field(
        name="New Member Count",
        value=f"{member.guild.member_count} members",
        inline=True,
    )

    # Add member avatar if available
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    elif member.guild.icon:
        embed.set_thumbnail(url=member.guild.icon.url)

    # Add footer
    embed.set_footer(
        text=f"ID: {member.id} • {member.guild.name}",
        icon_url=member.guild.icon.url if member.guild.icon else None,
    )

    return embed


async def generate_goodbye_message(member, language=None):
    """Generate a personalized goodbye message using LLM if available."""
    # If no language provided, get from persistent settings
    if language is None:
        language = await Translator.get_translation_language()

    # Default goodbye messages as fallback
    default_messages = [
        f"We'll miss you, {member.name}! Hope to see you again soon!",
        f"Sorry to see you go, {member.name}. The door is always open if you decide to return!",
        f"{member.name} has left the server. Wishing you all the best!",
        f"Until we meet again, {member.name}! Take care!",
        f"Farewell, {member.name}! Thank you for being part of our community!",
    ]

    # Try to use LLM for a personalized goodbye if configured
    if LLM.GOODBYE.API_KEY:
        try:
            llm_client = LLMClient(
                api_key=LLM.GOODBYE.API_KEY,
                api_url=LLM.GOODBYE.API_URL,
                model=LLM.GOODBYE.MODEL,
            )

            prompt = LLMMessage(
                role="user",
                content=f"""Generate a brief, thoughtful goodbye message for a Discord user named {member.name} 
                who just left the server {member.guild.name}.
                The message should be 1-2 sentences, respectful, and wishing them well.
                Don't use hashtags or emojis and only English.
                The server's primary language is {language}.
                """,
            )

            response = await llm_client.invoke(
                messages=[prompt], temperature=0.7, max_tokens=150
            )

            if response and len(response) > 10:
                return response

        except Exception as e:
            logger.error(f"Failed to generate LLM goodbye message: {str(e)}")

    # Fallback to random default message
    return random.choice(default_messages)

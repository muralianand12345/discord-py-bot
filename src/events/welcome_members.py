import random
import discord


from bot import bot, logger
from config import BOT, LLM
from utils.llm import LLMClient, LLMMessage


@bot.event
async def on_member_join(member):
    """Event handler for when a member joins the server."""
    # Skip if not in the configured guild
    if bot.guild_id and member.guild.id != bot.guild_id:
        return

    # Log the new member
    logger.info(
        f"Member joined: {member.name}#{member.discriminator} (ID: {member.id})"
    )

    # Translate the member's name to Japanese
    translated_name = await translate_name_to_japanese(member.name)

    # Set the new nickname
    try:
        if translated_name and translated_name != member.name:
            await member.edit(nick=translated_name)
            logger.info(f"Changed nickname for {member.name} to {translated_name}")
    except Exception as e:
        logger.error(f"Failed to set nickname for {member.name}: {str(e)}")

    # Assign the default role if configured
    if BOT.WELCOME.ROLE_ID:
        try:
            role = member.guild.get_role(int(BOT.WELCOME.ROLE_ID))
            if role:
                await member.add_roles(role)
                logger.info(f"Assigned role '{role.name}' to {member.name}")
            else:
                logger.warning(f"Role with ID {BOT.WELCOME.ROLE_ID} not found")
        except Exception as e:
            logger.error(f"Failed to assign role to {member.name}: {str(e)}")

    # Send welcome message if welcome channel is configured
    if BOT.WELCOME.WELCOME_CHANNEL_ID:
        try:
            channel = member.guild.get_channel(int(BOT.WELCOME.WELCOME_CHANNEL_ID))
            if channel:
                # Create and send welcome embed
                embed = await create_welcome_embed(member, translated_name)
                await channel.send(content=f"Welcome {member.mention}!", embed=embed)
            else:
                logger.warning(
                    f"Welcome channel with ID {BOT.WELCOME.WELCOME_CHANNEL_ID} not found"
                )
        except Exception as e:
            logger.error(f"Failed to send welcome message for {member.name}: {str(e)}")


async def create_welcome_embed(member, translated_name=None):
    """Creates a custom welcome embed for the new member."""
    embed = discord.Embed(
        title=f"Welcome to {member.guild.name}! 🎉",
        description=await generate_welcome_message(member, translated_name),
        color=0x5CDBF0,  # Light blue color
    )

    # Add member info
    embed.add_field(
        name="Member", value=f"{member.name} ({member.mention})", inline=True
    )

    # Add translated name if available
    if translated_name and translated_name != member.name:
        embed.add_field(name="Japanese Name", value=translated_name, inline=True)

    embed.add_field(
        name="Account Created",
        value=f"<t:{int(member.created_at.timestamp())}:R>",
        inline=True,
    )

    embed.add_field(
        name="Member Count", value=f"{member.guild.member_count} members", inline=False
    )

    # Add server image or member avatar
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


async def generate_welcome_message(member, translated_name=None):
    """Generate a personalized welcome message using LLM if available."""
    # Default welcome messages as fallback
    default_messages = [
        f"Welcome to our community, {member.name}! Feel free to introduce yourself!",
        f"So glad to have you with us, {member.name}! Make yourself at home!",
        f"A new friend has arrived! Welcome to {member.guild.name}, {member.name}!",
        f"The community just got better with {member.name} joining us!",
        f"Hello there, {member.name}! We're excited to have you join our server!",
    ]

    # Try to use LLM for a personalized welcome if configured
    if LLM.WELCOME.API_KEY:
        try:
            llm_client = LLMClient(
                api_key=LLM.WELCOME.API_KEY,
                api_url=LLM.WELCOME.API_URL,
                model=LLM.WELCOME.MODEL,
            )

            name_info = (
                f"Their name has been translated to Japanese as '{translated_name}'."
                if translated_name and translated_name != member.name
                else ""
            )

            prompt = LLMMessage(
                role="user",
                content=f"""Generate a friendly, warm welcome message for a new Discord user named {member.name} 
                who just joined the server {member.guild.name}.
                {name_info}
                The message should be 2-3 sentences, conversational, and welcoming.
                Don't use hashtags or emojis and only English.
                """,
            )

            response = await llm_client.invoke(
                messages=[prompt], temperature=0.7, max_tokens=150
            )

            if response and len(response) > 10:
                return response

        except Exception as e:
            logger.error(f"Failed to generate LLM welcome message: {str(e)}")

    # Fallback to random default message
    return random.choice(default_messages)


async def translate_name_to_japanese(name):
    """Translates a name to Japanese using LLM with retry and fallback."""
    # Skip translation if name is already in Japanese or contains non-latin characters
    if any(ord(char) > 127 for char in name):
        return name

    if LLM.TRANSLATOR.API_KEY:
        try:
            # Create LLM client with retry settings
            llm_client = LLMClient(
                api_key=LLM.TRANSLATOR.API_KEY,
                api_url=LLM.TRANSLATOR.API_URL,
                model=LLM.TRANSLATOR.MODEL,
                max_retries=3,
                retry_base_delay=1.0,
                retry_max_delay=8.0,
                request_timeout=10.0,
            )

            prompt = LLMMessage(
                role="user",
                content=f"""Translate the name "{name}" to Japanese.
                If the name has a common Japanese equivalent, use that.
                Otherwise, use phonetic katakana that sounds similar.
                Just provide the translated name without explanation.
                """,
            )

            # Define a fallback function that returns romanized Japanese if all else fails
            def get_simple_fallback():
                # Very simple romanization fallback
                katakana_map = {
                    "a": "ア",
                    "i": "イ",
                    "u": "ウ",
                    "e": "エ",
                    "o": "オ",
                    "ka": "カ",
                    "ki": "キ",
                    "ku": "ク",
                    "ke": "ケ",
                    "ko": "コ",
                    "sa": "サ",
                    "shi": "シ",
                    "su": "ス",
                    "se": "セ",
                    "so": "ソ",
                    "ta": "タ",
                    "chi": "チ",
                    "tsu": "ツ",
                    "te": "テ",
                    "to": "ト",
                    "na": "ナ",
                    "ni": "ニ",
                    "nu": "ヌ",
                    "ne": "ネ",
                    "no": "ノ",
                    "ha": "ハ",
                    "hi": "ヒ",
                    "fu": "フ",
                    "he": "ヘ",
                    "ho": "ホ",
                    "ma": "マ",
                    "mi": "ミ",
                    "mu": "ム",
                    "me": "メ",
                    "mo": "モ",
                    "ya": "ヤ",
                    "yu": "ユ",
                    "yo": "ヨ",
                    "ra": "ラ",
                    "ri": "リ",
                    "ru": "ル",
                    "re": "レ",
                    "ro": "ロ",
                    "wa": "ワ",
                    "wo": "ヲ",
                    "n": "ン",
                }

                # Simple romanization - not perfect but a decent fallback
                result = ""
                name_lower = name.lower()
                i = 0
                while i < len(name_lower):
                    for syllable in sorted(katakana_map.keys(), key=len, reverse=True):
                        if name_lower[i:].startswith(syllable):
                            result += katakana_map[syllable]
                            i += len(syllable)
                            break
                    else:
                        # If no match, just skip this character
                        i += 1

                # If result is empty, just return the original name
                return result if result else name

            # Use the with_fallback method to automatically handle retries and fallback
            response = await llm_client.with_fallback(
                messages=[prompt],
                fallback_fn=get_simple_fallback,
                temperature=0.3,
                max_tokens=50,
            )

            # Clean up the response
            if response:
                # Remove any explanations, just get the name
                response = response.strip()
                # Remove any quotes that might be in the response
                response = response.replace('"', "").replace("'", "")
                # If response is too long, trim it
                if len(response) > 15:
                    # Try to find where the actual name ends
                    for char in [".", ",", "\n", " "]:
                        if char in response:
                            response = response.split(char)[0]

                return response

        except Exception as e:
            logger.error(f"Failed to translate name using LLM: {str(e)}")

    # Return original name if translation fails
    return name

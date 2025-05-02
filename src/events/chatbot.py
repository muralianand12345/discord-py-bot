import os
import json
import discord
from datetime import datetime
from typing import Dict, List, Optional

from bot import bot, logger
from config import LLM
from utils.llm import LLMClient, LLMMessage


# Constants
HISTORY_DIR = os.path.dirname(LLM.CHATBOT.BOT_CONFIG.CHATBOT_HISTORY_FILE)
os.makedirs(HISTORY_DIR, exist_ok=True)

# Chat histories by channel ID
chat_histories: Dict[str, List[Dict[str, str]]] = {}

# Load existing chat histories
try:
    if os.path.exists(LLM.CHATBOT.BOT_CONFIG.CHATBOT_HISTORY_FILE):
        with open(
            LLM.CHATBOT.BOT_CONFIG.CHATBOT_HISTORY_FILE, "r", encoding="utf-8"
        ) as f:
            chat_histories = json.load(f)
            logger.info(f"Loaded chat histories for {len(chat_histories)} channels")
except Exception as e:
    logger.error(f"Failed to load chat histories: {str(e)}")
    chat_histories = {}


async def save_chat_histories():
    """Save chat histories to file."""
    try:
        with open(
            LLM.CHATBOT.BOT_CONFIG.CHATBOT_HISTORY_FILE, "w", encoding="utf-8"
        ) as f:
            json.dump(chat_histories, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save chat histories: {str(e)}")


@bot.event
async def on_message(message: discord.Message):
    """Handle incoming messages for the chatbot."""
    # Skip messages from bots
    if message.author.bot:
        return

    # Skip if not in the configured guild
    if bot.guild_id and message.guild and message.guild.id != bot.guild_id:
        return

    # Process commands first
    await bot.process_commands(message)

    # Only respond in the designated channel
    if str(message.channel.id) != LLM.CHATBOT.BOT_CONFIG.CHANNEL_ID:
        return

    # Get or initialize channel history
    channel_id = str(message.channel.id)
    if channel_id not in chat_histories:
        chat_histories[channel_id] = []

    # Get user details
    user_id = str(message.author.id)
    user_name = message.author.display_name
    user_discriminator = (
        message.author.discriminator
        if hasattr(message.author, "discriminator")
        else "0000"
    )
    user_roles = [role.name for role in message.author.roles] if message.guild else []
    user_top_role = (
        message.author.top_role.name
        if message.guild and message.author.top_role
        else "None"
    )

    # Add user message to history with user ID
    chat_histories[channel_id].append(
        {
            "role": "user",
            "user_id": user_id,
            "name": user_name,
            "content": message.content,
            "timestamp": datetime.now().isoformat(),
        }
    )

    # Trim history if it exceeds the maximum length
    max_history = int(LLM.CHATBOT.BOT_CONFIG.CHATBOT_MAX_HISTORY)
    if len(chat_histories[channel_id]) > max_history * 2:
        chat_histories[channel_id] = chat_histories[channel_id][-max_history * 2 :]

    # Process the message and generate a response
    async with message.channel.typing():
        response = await generate_response(
            channel_id,
            user_id,
            user_name,
            user_discriminator,
            user_roles,
            user_top_role,
        )

    # Send response, ensuring it doesn't exceed Discord's character limit
    if response:
        # Truncate response if it's too long (Discord limit is 2000 characters)
        if len(response) > 1990:  # Leave some buffer
            truncated_response = response[:1990] + "..."
            logger.warning(
                f"Response was truncated from {len(response)} characters to 1990 characters"
            )
            response = truncated_response

        try:
            sent_message = await message.reply(response)
        except discord.NotFound:
            sent_message = await message.channel.send(response)
        except discord.Forbidden:
            logger.error(
                "Bot does not have permission to send messages in this channel."
            )
            return
        except discord.HTTPException as e:
            logger.error(f"Failed to send message: {str(e)}")

            # Try to send a shorter message if we still encountered an error
            if len(response) > 1000:
                try:
                    short_response = "I had a lot to say, but Discord won't let me send such a long message. Here's a shorter response:"
                    short_response += "\n\n" + response[:900] + "..."
                    sent_message = await message.reply(short_response)
                except Exception as e2:
                    logger.error(f"Failed to send shortened message: {str(e2)}")
                    return
            return

        # Add bot response to history
        chat_histories[channel_id].append(
            {
                "role": "assistant",
                "name": LLM.CHATBOT.BOT_CONFIG.BOT_NAME,
                "content": response,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Save updated history
        await save_chat_histories()


async def generate_response(
    channel_id: str,
    user_id: str,
    user_name: str,
    user_discriminator: str,
    user_roles: List[str],
    user_top_role: str,
) -> Optional[str]:
    """Generate a response using the LLM with context from chat history."""
    if not LLM.CHATBOT.API_KEY:
        logger.warning("No API key configured for chatbot LLM")
        return "I'm sorry, but I'm not fully configured yet."

    try:
        # Create LLM client
        llm_client = LLMClient(
            api_key=LLM.CHATBOT.API_KEY,
            api_url=LLM.CHATBOT.API_URL,
            model=LLM.CHATBOT.MODEL,
            max_retries=2,
            retry_base_delay=1.0,
            retry_max_delay=4.0,
            request_timeout=15.0,
        )

        # Build messages for context
        messages = []

        # Format roles for prompt
        roles_info = ", ".join(user_roles[:3]) if user_roles else "No special roles"
        if len(user_roles) > 3:
            roles_info += f" and {len(user_roles) - 3} more"

        # System prompt to set the tone and behavior
        system_prompt = LLMMessage(
            role="system",
            content=f"""You are {LLM.CHATBOT.BOT_CONFIG.BOT_NAME}, a friendly and helpful Discord bot. 
            You are chatting in a Discord server with multiple users.
            
            USER INFORMATION:
            - User ID: {user_id}
            - Username: {user_name}#{user_discriminator}
            - Top Role: {user_top_role}
            - Roles: {roles_info}
            
            IMPORTANT GUIDELINES:
            - Keep your responses concise and friendly
            - Be conversational but brief (1-3 sentences unless a longer explanation is needed)
            - Keep your conversation in English unless requested otherwise
            - Make sure responses are formatted as per Discord's markdown rules
            - Keep responses under 1,800 characters to avoid Discord message length limitations
            - Use discord features like **bold**, *italic*, `code`, ```code blocks``` appropriately
            
            Track users by their unique user ID ({user_id}), not just their display name, 
            as users may change their display names but will keep the same user ID.
            """,
        )
        messages.append(system_prompt)

        # Add chat history for context
        history = chat_histories[channel_id]
        # Only use the most recent history up to max_history
        max_history = int(LLM.CHATBOT.BOT_CONFIG.CHATBOT_MAX_HISTORY)
        recent_history = (
            history[-max_history * 2 :] if len(history) > max_history * 2 else history
        )

        # Add user identifiers to messages before sending to LLM
        for entry in recent_history:
            # Skip entries without proper role or content
            if "role" not in entry or "content" not in entry:
                continue

            content = entry["content"]

            # For user messages, add identifier prefix
            if entry["role"] == "user":
                user_identifier = entry.get("user_id", "unknown")
                user_display = entry.get("name", "User")
                modified_content = (
                    f"[User {user_identifier} ({user_display})]: {content}"
                )
                messages.append(LLMMessage(role="user", content=modified_content))
            else:
                messages.append(LLMMessage(role=entry["role"], content=content))

        # Generate response
        response = await llm_client.invoke(
            messages=messages,
            max_tokens=200,  # Reduced to help keep responses shorter
        )

        return response.strip()

    except Exception as e:
        logger.error(f"Failed to generate chatbot response: {str(e)}")
        return "I'm having trouble thinking right now. Can you try again in a moment?"

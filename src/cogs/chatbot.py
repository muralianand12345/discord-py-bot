"""
Chatbot functionality for Discord bot with enhanced intelligence, context awareness, and reliability.
"""

import asyncio
import datetime
import logging
import random
import re
import traceback
from typing import Dict, List, Optional, Set, Tuple

import discord
from discord.ext import commands

from utils.db_manager import DatabaseManager
from utils.llm import LLM
from utils.settings import (
    CHATBOT_CHANNELS,
    CHATBOT_ENABLED,
    CHATBOT_MAX_HISTORY,
    CHATBOT_MAX_TOKENS,
    CHATBOT_NAME,
    PROMPTS,
)


class ChatbotCog(commands.Cog, name="Chatbot"):
    """AI-powered chatbot for natural group conversations in channels."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger("chatbot_cog")
        self.llm = LLM()
        self.db = DatabaseManager()
        self.is_enabled = CHATBOT_ENABLED

        # Critical: Ensure channels are properly initialized from settings
        # Convert any string IDs to integers if needed
        self.target_channels = []
        for channel in CHATBOT_CHANNELS:
            if isinstance(channel, str) and channel.isdigit():
                self.target_channels.append(int(channel))
            elif isinstance(channel, int):
                self.target_channels.append(channel)

        # Add extra diagnostic log
        self.logger.info(f"Chatbot initialized with channels: {self.target_channels}")

        self.typing_lock = {}  # Tracks channels where the bot is "typing"
        self.recent_questions = {}  # Tracks recent questions to detect repeats
        self.recent_topics = {}  # Tracks conversation topics per channel
        self.user_info = {}  # Tracks information about users

        # Add message handling statistics for diagnostics
        self.stats = {
            "messages_received": 0,
            "responses_sent": 0,
            "response_failures": 0,
            "last_active": datetime.datetime.utcnow(),
        }

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle incoming messages for the chatbot with improved reliability."""
        # Skip messages from bots to avoid loops
        if message.author.bot:
            return

        # Skip processing if chatbot is disabled
        if not self.is_enabled:
            return

        # Skip if message is a command
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        # Check if message is in a monitored channel
        if message.channel.id in self.target_channels:
            content = message.content.strip()
        else:
            return

        # If we have content in a monitored channel, process it
        if content:
            # Update statistics
            self.stats["messages_received"] += 1
            self.stats["last_active"] = datetime.datetime.utcnow()

            # Log the incoming message to help with debugging
            self.logger.info(
                f"Received message from {message.author.display_name}: '{content}'"
            )

            # Store user info for personalization
            self._update_user_info(message.author)

            # Check if message is a repeat
            is_repeat = self._check_repeated_question(
                message.channel.id, message.author.id, content
            )

            # Calculate if we should respond - IMPORTANT CHANGE: MORE RELIABLE RESPONSE DECISION
            should_respond = self._should_respond_enhanced(
                message.channel.id, message, content
            )

            if not should_respond:
                self.logger.info(
                    f"Decided not to respond to {message.author.display_name}'s message"
                )
                return

            # Start typing indicator with variable duration based on message complexity
            typing_duration = min(
                1.5 + (len(content) * 0.01), 3.0
            )  # Between 1.5-3 seconds
            await self._set_typing(message.channel, True, typing_duration)

            try:
                # Get channel conversation history
                conversation_history = await self._get_channel_history(
                    message.channel.id
                )

                # Update conversation topics
                self._update_conversation_topics(message.channel.id, content)

                # Add the current message to history
                current_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                conversation_history.append(
                    {
                        "role": "user",
                        "username": message.author.display_name,
                        "content": content,
                        "timestamp": current_time,
                        "user_id": message.author.id,
                        "channel_id": message.channel.id,
                    }
                )

                # Response retry mechanism with backoff
                max_retries = 2
                response = None

                for attempt in range(max_retries + 1):
                    try:
                        # Generate a response with enhanced context
                        response = await self._generate_intelligent_response_with_retry(
                            conversation_history, message.author, is_repeat=is_repeat
                        )

                        # Check for response quality
                        if not self._is_valid_response(response, content):
                            if attempt < max_retries:
                                self.logger.warning(
                                    f"Generated invalid response on attempt {attempt+1}, retrying..."
                                )
                                continue
                            response = self._get_fallback_response(content)

                        # Quality checks passed, break out of retry loop
                        break

                    except Exception as e:
                        self.logger.error(
                            f"Error on response attempt {attempt+1}: {str(e)}"
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(0.5 * (attempt + 1))  # Backoff delay
                        else:
                            response = self._get_fallback_response(content)

                # Ensure we have a valid response
                if not response:
                    response = self._get_fallback_response(content)

                # Clean the response
                response = self._clean_response(response, conversation_history)

                # Add the bot's response to history
                current_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                conversation_history.append(
                    {
                        "role": "assistant",
                        "username": CHATBOT_NAME,
                        "content": response,  # Store unformatted for future context
                        "timestamp": current_time,
                        "user_id": self.bot.user.id,
                        "channel_id": message.channel.id,
                    }
                )

                # Save the updated conversation history
                await self._save_channel_history(
                    message.channel.id, conversation_history
                )

                # Send the response with variable delay
                delay = random.uniform(
                    0.3, 0.8
                )  # Reduced delay for better responsiveness
                await asyncio.sleep(delay)

                # Send the message with error handling
                try:
                    # Split very long responses into multiple messages for more natural flow
                    if len(response) > 1500:
                        chunks = self._smart_chunk_message(response)
                        for i, chunk in enumerate(chunks):
                            await message.channel.send(chunk)
                            if i < len(chunks) - 1:
                                await asyncio.sleep(0.8)  # Slight delay between chunks
                    else:
                        await message.channel.send(response)

                    # Update statistics
                    self.stats["responses_sent"] += 1
                    self.logger.info(
                        f"Successfully sent response to {message.author.display_name}"
                    )

                except discord.HTTPException as e:
                    self.logger.error(f"Failed to send message: {str(e)}")
                    # Try one more time with a simpler message if the send fails
                    try:
                        await message.channel.send(
                            "Hmm, had trouble sending my response. Let me try again..."
                        )
                        await message.channel.send(
                            response[:1900] + "..."
                            if len(response) > 1900
                            else response
                        )
                        self.stats["responses_sent"] += 1
                    except Exception as e2:
                        self.logger.error(
                            f"Second attempt to send message failed: {str(e2)}"
                        )
                        self.stats["response_failures"] += 1

            except Exception as e:
                self.logger.error(f"Critical error in message handling: {str(e)}")
                self.logger.error(traceback.format_exc())
                self.stats["response_failures"] += 1

                # Always try to respond even on error
                try:
                    await message.channel.send(
                        "Sorry, I got distracted for a second there. What were we talking about?"
                    )
                except:
                    pass  # Last resort - if we can't send anything, just continue

            finally:
                # Always stop typing indicator
                await self._set_typing(message.channel, False)

    def _should_respond_enhanced(
        self, channel_id: int, message: discord.Message, content: str
    ) -> bool:
        """
        Enhanced decision mechanism for when to respond, with higher responsiveness.

        Args:
            channel_id: The channel ID
            message: The message object
            content: The message content

        Returns:
            Boolean indicating whether to respond
        """
        # First, let's handle direct questions - ALWAYS respond to these
        if re.search(r"\?$", content) or re.search(
            r"\b(what|how|why|when|who|where|is|are|can|could|would|should|did)\b",
            content.lower(),
        ):
            return True

        # Always respond to direct addresses (mentioning the bot's name or variants)
        if (
            CHATBOT_NAME.lower() in content.lower()
            or "bot" in content.lower()
            or "lee" in content.lower()
        ):
            return True

        # Get conversation history
        history = self._get_recent_messages(channel_id)

        # If this is the first message in the channel, respond
        if not history:
            return True

        # If the message is very short (like "hi", "hello"), always respond
        if len(content) <= 5:
            return True

        # If bot was the last speaker, be more selective about responding again
        if history and history[-1].get("user_id") == self.bot.user.id:
            # Check time since last bot message
            try:
                last_time = datetime.datetime.strptime(
                    history[-1].get("timestamp", ""), "%Y-%m-%d %H:%M:%S"
                )
                current_time = datetime.datetime.utcnow()
                time_diff = (current_time - last_time).total_seconds()

                # If it's been less than a few seconds and not a direct question/mention, don't respond
                # This prevents double-responses but allows for quick follow-ups to questions
                if time_diff < 10 and not any(
                    [
                        CHATBOT_NAME.lower() in content.lower(),
                        "bot" in content.lower(),
                        "lee" in content.lower(),
                        re.search(r"\?$", content),
                        re.search(
                            r"\b(what|how|why|when|who|where|is|are|can|could|would|should|did)\b",
                            content.lower(),
                        ),
                    ]
                ):
                    return False
            except ValueError:
                # If datetime parsing fails, just continue (shouldn't happen with proper formatting)
                pass

        # IMPORTANT: Higher base response chance - 80% for most messages
        response_chance = 0.8

        # Generate random number and compare with response chance
        return random.random() < response_chance

    def _check_repeated_question(
        self, channel_id: int, user_id: int, content: str
    ) -> bool:
        """
        Check if a user is repeating a similar question or message.

        Args:
            channel_id: The channel ID
            user_id: The user ID
            content: The message content

        Returns:
            Boolean indicating if it's a repeat
        """
        # Initialize channel in tracking dict if needed
        if channel_id not in self.recent_questions:
            self.recent_questions[channel_id] = {}

        # Initialize user in channel tracking if needed
        if user_id not in self.recent_questions[channel_id]:
            self.recent_questions[channel_id][user_id] = []

        # Clean up old questions (older than 10 minutes)
        current_time = datetime.datetime.utcnow()
        self.recent_questions[channel_id][user_id] = [
            (q, t)
            for q, t in self.recent_questions[channel_id][user_id]
            if (current_time - t).total_seconds() < 600
        ]

        # Check for similarity with recent questions
        content_lower = content.lower()
        for q, _ in self.recent_questions[channel_id][user_id]:
            # Check for exact matches or very similar questions
            if content_lower == q.lower() or (
                # Fuzzy match for questions with most words the same
                sum(w in q.lower() for w in content_lower.split())
                > len(content_lower.split()) * 0.7
            ):
                # Add the new question but mark as repeat
                self.recent_questions[channel_id][user_id].append(
                    (content, current_time)
                )
                return True

        # Not a repeat, add to tracking
        self.recent_questions[channel_id][user_id].append((content, current_time))
        return False

    def _update_user_info(self, user: discord.Member):
        """
        Update tracked information about a user for more personalized responses.

        Args:
            user: The Discord user
        """
        if user.id not in self.user_info:
            self.user_info[user.id] = {
                "name": user.display_name,
                "first_seen": datetime.datetime.utcnow(),
                "roles": [role.name for role in user.roles if role.name != "@everyone"],
                "mentioned_topics": set(),
                "interactions": 0,
            }

        # Update interaction count
        self.user_info[user.id]["interactions"] += 1

        # Update roles in case they changed
        self.user_info[user.id]["roles"] = [
            role.name for role in user.roles if role.name != "@everyone"
        ]

    def _update_conversation_topics(self, channel_id: int, content: str):
        """
        Extract and track conversation topics to maintain better context.

        Args:
            channel_id: The channel ID
            content: The message content
        """
        if channel_id not in self.recent_topics:
            self.recent_topics[channel_id] = set()

        # Simple keyword extraction (could be improved with NLP)
        # Extract nouns and meaningful terms
        content_lower = content.lower()
        words = re.findall(r"\b[a-z]{4,}\b", content_lower)

        # Filter out common stop words
        stop_words = {
            "this",
            "that",
            "then",
            "than",
            "they",
            "them",
            "their",
            "have",
            "from",
            "with",
            "would",
            "could",
            "should",
            "about",
            "what",
            "which",
            "when",
            "where",
            "been",
            "just",
            "your",
            "very",
        }
        topics = [word for word in words if word not in stop_words]

        # Add to recent topics, limiting to 10 most recent
        self.recent_topics[channel_id].update(topics)
        if len(self.recent_topics[channel_id]) > 10:
            # Convert to list to remove random elements
            topics_list = list(self.recent_topics[channel_id])
            self.recent_topics[channel_id] = set(topics_list[-10:])

    async def _generate_intelligent_response_with_retry(
        self,
        conversation_history: List[Dict],
        user: discord.Member,
        is_repeat: bool = False,
    ) -> str:
        """
        Generate a response with retry logic and content screening, with enhanced Discord formatting.

        Args:
            conversation_history: The conversation history
            user: The Discord user
            is_repeat: Whether it's a repeated question

        Returns:
            Generated response text
        """
        current_message = conversation_history[-1]["content"]
        current_user = conversation_history[-1]["username"]
        user_id = conversation_history[-1]["user_id"]

        # Format the conversation history
        formatted_history = self._format_conversation_history(conversation_history)

        # Get basic system message
        system_message = PROMPTS["chatbot"]["system_message"]

        # Build enhanced context with Discord formatting information
        enhanced_context = self._build_enhanced_context(
            conversation_history, user, is_repeat
        )

        # Add specific instructions for Discord formatting
        discord_formatting = f"""
        IMPORTANT DISCORD FORMATTING INSTRUCTIONS:
        
        1. When referring to users, use their Discord mention format: <@{user_id}>
        2. When referring to timestamps or dates:
        - For the current time: <t:{int(datetime.datetime.utcnow().timestamp())}:R>
        - For a specific time: <t:unix_timestamp:R>
        3. Use appropriate formatting like **bold**, *italics*, and `code` to make your messages more readable
        4. If providing a list of information (like news), consider formatting with numbers and proper spacing
        
        Additionally:
        1. Provide direct, confident answers rather than asking for clarification
        2. Be conversational but information-dense
        3. Avoid phrases like "I don't have real-time information" - if asked about news, provide plausible information
        4. Keep responses engaging but concise
        """

        # Create the LLM message payload
        messages = [
            {"role": "system", "content": system_message},
            {"role": "system", "content": enhanced_context},
            {"role": "system", "content": discord_formatting},
        ]

        # Add conversation history for context
        if formatted_history:
            messages.append(
                {
                    "role": "system",
                    "content": f"Recent conversation history:\n{formatted_history}",
                }
            )

        # Add the current message as the last user message
        messages.append(
            {"role": "user", "content": f"{current_user} said: {current_message}"}
        )

        try:
            # Note: Removed temperature parameter as it's not supported by Groq
            response = await self.llm.invoke(messages, max_tokens=CHATBOT_MAX_TOKENS)

            return (
                response
                if response
                else "Hmm, interesting point. What else is on your mind?"
            )
        except Exception as e:
            self.logger.error(f"LLM invocation failed: {str(e)}")
            raise

    def _format_timestamps_in_response(self, response: str) -> str:
        """
        Format any generic time references in the response to proper Discord timestamp format.

        Args:
            response: The response text

        Returns:
            Response with Discord-formatted timestamps
        """
        now = datetime.datetime.utcnow()
        unix_now = int(now.timestamp())

        # Replace obvious time references
        replacements = {
            "current time": f"<t:{unix_now}:T>",
            "current date": f"<t:{unix_now}:D>",
            "current date and time": f"<t:{unix_now}:F>",
            "right now": f"<t:{unix_now}:R>",
            "today": f"<t:{unix_now}:D>",
            "yesterday": f"<t:{int((now - datetime.timedelta(days=1)).timestamp())}:D>",
            "tomorrow": f"<t:{int((now + datetime.timedelta(days=1)).timestamp())}:D>",
        }

        for text, replacement in replacements.items():
            response = re.sub(
                r"\b" + re.escape(text) + r"\b",
                replacement,
                response,
                flags=re.IGNORECASE,
            )

        return response

    def _clean_response(self, response: str, conversation_history: List[Dict]) -> str:
        """
        Clean and fix potential issues in the response.

        Args:
            response: The response text
            conversation_history: The conversation history

        Returns:
            Cleaned response text
        """
        if not response:
            return "Hmm, interesting point. What else is on your mind?"

        # Remove any prefix that looks like the bot is quoting itself
        response = re.sub(r"^(\*\*)?Lee:(\*\*)?\s*", "", response)
        response = re.sub(r"^(\*\*)?Bot:(\*\*)?\s*", "", response)
        response = re.sub(r"^(\*\*)?Assistant:(\*\*)?\s*", "", response)

        # Detect if response is too similar to a recent bot message
        recent_bot_messages = [
            msg.get("content", "")
            for msg in conversation_history[-10:]
            if msg.get("role") == "assistant"
        ]

        for past_msg in recent_bot_messages:
            # Check for high similarity
            if (
                past_msg
                and response
                and self._calculate_similarity(response, past_msg) > 0.7
            ):
                # If too similar, adjust the response
                return f"{response}\n\nAnyway, what's been keeping you busy lately?"

        return response

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        # Convert to lowercase and tokenize
        t1 = set(text1.lower().split())
        t2 = set(text2.lower().split())

        # Calculate Jaccard similarity
        if not t1 or not t2:
            return 0

        intersection = len(t1.intersection(t2))
        union = len(t1.union(t2))

        return intersection / union if union > 0 else 0

    def _is_valid_response(self, response: str, user_message: str) -> bool:
        """
        Check if a generated response is valid and appropriate.

        Args:
            response: The generated response
            user_message: The user's message

        Returns:
            Boolean indicating if response is valid
        """
        if not response or len(response.strip()) < 2:
            return False

        # Check for repetition of the user's message
        if user_message and len(user_message) > 5:
            similarity = self._calculate_similarity(response, user_message)
            if similarity > 0.8:  # If response is too similar to user message
                return False

        # Check for forbidden phrases
        forbidden_phrases = [
            "I'm an AI",
            "As an AI",
            "I'm just a",
            "I don't have personal",
            "I don't have the ability to",
            "I cannot",
            "I'm not able to",
        ]

        if any(phrase.lower() in response.lower() for phrase in forbidden_phrases):
            return False

        return True

    def _get_fallback_response(self, user_message: str) -> str:
        """
        Get a fallback response when generation fails.

        Args:
            user_message: The user's message

        Returns:
            Fallback response
        """
        fallbacks = [
            "That's an interesting point. Tell me more about what you think?",
            "I see what you mean. What else is on your mind?",
            "Nice! How's your day going so far?",
            "Cool. What else have you been up to lately?",
            "I hear you. Anything else you want to chat about?",
            "Got it. What else is happening?",
            "Interesting! Have you always felt that way?",
            "Makes sense. What else is new with you?",
        ]

        # Check if it's a greeting
        if re.match(
            r"^(hi|hello|hey|yo|sup|hiya|greetings|howdy)\b", user_message.lower()
        ):
            greeting_responses = [
                "Hey there! What's up?",
                "Hi! How's it going?",
                "Hello! What's new?",
                "Hey! How's your day been?",
                "What's good? How are things?",
            ]
            return random.choice(greeting_responses)

        # Check if it's a question
        if re.search(r"\?$", user_message) or re.search(
            r"\b(what|how|why|when|who|where|is|are|can|could|would|should|did)\b",
            user_message.lower(),
        ):
            question_responses = [
                "Hmm, let me think about that for a sec...",
                "That's a good question. What do you think?",
                "Interesting question! I'm curious about your thoughts on that.",
                "I've been wondering about that too, actually.",
            ]
            return random.choice(question_responses)

        return random.choice(fallbacks)

    def _build_enhanced_context(
        self, conversation_history: List[Dict], user: discord.Member, is_repeat: bool
    ) -> str:
        """
        Build enhanced context information with Discord formatting instructions.

        Args:
            conversation_history: List of conversation messages
            user: The Discord user who sent the message
            is_repeat: Whether the user is repeating a question

        Returns:
            Enhanced context string
        """
        context_parts = []

        # Add conversation dynamics context
        active_users = self._get_active_users(conversation_history)
        context_parts.append(
            f"Currently active users in this conversation: {', '.join(active_users)}.\n"
        )

        # Add information about the current user with ID for tagging
        user_info = self.user_info.get(user.id, {})
        user_roles = user_info.get("roles", [])

        # Explicitly provide the user's ID for mentions
        context_parts.append(
            f"You're talking to {user.display_name}. Their user ID is {user.id}. "
            f"To mention them in your response, use: <@{user.id}>\n"
        )

        if user_roles:
            role_info = (
                f"User {user.display_name} has these roles: {', '.join(user_roles)}."
            )
            context_parts.append(role_info + "\n")

        # Add Discord formatting instruction with current timestamp
        current_timestamp = int(datetime.datetime.utcnow().timestamp())
        context_parts.append(
            f"Current Unix timestamp is {current_timestamp}. "
            f"Use Discord timestamp formatting like <t:{current_timestamp}:R> for relative time ('just now'), "
            f"<t:{current_timestamp}:F> for full date and time, or <t:{current_timestamp}:D> for date only.\n"
        )

        # Add conversation topics
        channel_id = (
            conversation_history[0].get("channel_id") if conversation_history else None
        )
        if (
            channel_id
            and channel_id in self.recent_topics
            and self.recent_topics[channel_id]
        ):
            topics = ", ".join(self.recent_topics[channel_id])
            context_parts.append(f"Recent conversation topics: {topics}.\n")

            # Add channel mention formatting
            context_parts.append(
                f"The current channel ID is {channel_id}. To mention this channel, use: <#{channel_id}>\n"
            )

        # Add special handling guidance for repeated questions
        if is_repeat:
            context_parts.append(
                "NOTE: The user appears to be asking a similar question to one they asked recently. "
                "They may not have understood your previous answer or are looking for more information. "
                "Try to elaborate or explain differently.\n"
            )

        # Set the bot's role in this conversation
        context_parts.append(
            "In this conversation, you are an intelligent bot that is casually chatting with users. "
            "Keep responses genuine, friendly, and focused on whatever topics the users bring up. "
            "Use Discord's special formatting features like user mentions, timestamps, and channel mentions when appropriate.\n"
        )

        # Add some personality guidance
        context_parts.append(
            "Your personality: Be witty but not too random. Show genuine interest in the conversation. "
            "Occasionally be gently humorous. Remember facts about users. Use casual language but not too much slang. "
            "When discussing topics you know about, be helpful but not lecturing. Sound natural, not scripted."
        )

        return "\n".join(context_parts)

    def _get_active_users(self, conversation_history: List[Dict]) -> List[str]:
        """
        Extract unique active users from recent conversation history.

        Args:
            conversation_history: List of conversation messages

        Returns:
            List of active usernames
        """
        # Get last 6 messages
        recent_history = (
            conversation_history[-6:]
            if len(conversation_history) > 6
            else conversation_history
        )

        # Extract unique usernames
        usernames = set()
        for message in recent_history:
            if message.get("role") == "user":
                usernames.add(message.get("username", ""))

        return list(usernames)

    def _format_conversation_history(self, history: List[Dict]) -> str:
        """
        Format the group conversation history for the LLM prompt.

        Args:
            history: List of conversation messages

        Returns:
            Formatted conversation history text
        """
        # Skip the last message as it will be added separately
        if len(history) <= 1:
            return ""

        # Take just the most recent messages for context (last 8)
        history_to_format = history[-9:-1] if len(history) > 9 else history[:-1]

        # Get the format template
        format_template = PROMPTS["chatbot"]["context_format"]

        # Format each message
        formatted_messages = []
        for message in history_to_format:
            formatted_message = format_template.format(
                timestamp=message.get("timestamp", ""),
                username=message.get("username", "User"),
                message=message.get("content", ""),
            )
            formatted_messages.append(formatted_message)

        return "".join(formatted_messages)

    def _smart_chunk_message(self, message: str, max_length: int = 1500) -> List[str]:
        """
        Intelligently split a long message into chunks at appropriate breaking points.

        Args:
            message: The message to split
            max_length: Maximum length of each chunk

        Returns:
            List of message chunks
        """
        if len(message) <= max_length:
            return [message]

        chunks = []
        current_chunk = ""

        # Split by paragraphs first
        paragraphs = message.split("\n\n")

        for para in paragraphs:
            # If paragraph fits in current chunk, add it
            if len(current_chunk) + len(para) + 2 <= max_length:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            # If paragraph is too long, split by sentences
            elif len(para) > max_length:
                # Add current chunk if not empty
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # Split long paragraph by sentences
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= max_length:
                        if current_chunk:
                            current_chunk += " " + sentence
                        else:
                            current_chunk = sentence
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sentence
            # Otherwise start a new chunk
            else:
                chunks.append(current_chunk)
                current_chunk = para

        # Add final chunk if not empty
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _get_recent_messages(self, channel_id: int) -> List[Dict]:
        """
        Get recent messages from a channel's history.

        Args:
            channel_id: ID of the Discord channel

        Returns:
            List of recent messages
        """
        # Create a key for the channel
        channel_key = f"channel:{channel_id}"

        # Get channel data from the database
        guild_data = self.db.get_guild_settings(channel_id)

        # Return empty list if no history
        if "chatbot" not in guild_data or channel_key not in guild_data["chatbot"]:
            return []

        # Get conversation history
        conversation = guild_data["chatbot"].get(channel_key, [])

        return conversation

    async def _get_channel_history(self, channel_id: int) -> List[Dict]:
        """
        Retrieve conversation history for a channel from the database.

        Args:
            channel_id: ID of the Discord channel

        Returns:
            List of conversation messages
        """
        # Create a key for the channel
        channel_key = f"channel:{channel_id}"

        # Get channel data from the database
        guild_data = self.db.get_guild_settings(channel_id)

        # Initialize chatbot dict if it doesn't exist
        if "chatbot" not in guild_data:
            guild_data["chatbot"] = {}

        # Initialize or get this specific channel's history
        if channel_key not in guild_data["chatbot"]:
            guild_data["chatbot"][channel_key] = []

        # Get conversation history
        conversation = guild_data["chatbot"].get(channel_key, [])

        # Add channel_id to each message for reference
        for message in conversation:
            if "channel_id" not in message:
                message["channel_id"] = channel_id

        # Limit history to the maximum allowed
        if len(conversation) > CHATBOT_MAX_HISTORY:
            conversation = conversation[-CHATBOT_MAX_HISTORY:]

        return conversation

    async def _save_channel_history(self, channel_id: int, history: List[Dict]) -> None:
        """
        Save channel conversation history to the database.

        Args:
            channel_id: ID of the Discord channel
            history: List of conversation messages to save
        """
        # Create a key for the channel
        channel_key = f"channel:{channel_id}"

        # Get guild data from the database
        guild_data = self.db.get_guild_settings(channel_id)

        # Initialize chatbot dict if it doesn't exist
        if "chatbot" not in guild_data:
            guild_data["chatbot"] = {}

        # Limit history to the maximum allowed
        if len(history) > CHATBOT_MAX_HISTORY:
            history = history[-CHATBOT_MAX_HISTORY:]

        # Save the conversation
        guild_data["chatbot"][channel_key] = history

        # Update the database
        success = self.db.save_guild_settings(channel_id, guild_data)

        if not success:
            self.logger.error(
                f"Failed to save conversation history for channel {channel_id}"
            )

    async def _set_typing(
        self, channel: discord.TextChannel, is_typing: bool, duration: float = 3.0
    ) -> None:
        """
        Start or stop typing indicator in a channel.

        Args:
            channel: Discord channel to set typing status in
            is_typing: True to start typing, False to stop
            duration: How long to type for (max)
        """
        # Use a lock to avoid multiple typing indicators
        if channel.id not in self.typing_lock:
            self.typing_lock[channel.id] = False

        # If already in the requested state, do nothing
        if self.typing_lock[channel.id] == is_typing:
            return

        self.typing_lock[channel.id] = is_typing

        if is_typing:
            # Start typing indicator
            async with channel.typing():
                # Wait until typing is turned off or max duration
                for _ in range(int(duration * 10)):  # duration * 10 iterations of 0.1s
                    if not self.typing_lock[channel.id]:
                        break
                    await asyncio.sleep(0.1)

    @commands.command(name="chatbot")
    @commands.has_permissions(administrator=True)
    async def chatbot_command(self, ctx: commands.Context, action: str, *args):
        """
        Control the chatbot functionality.

        Args:
            action: Action to perform (enable, disable, status, clear)
            args: Additional arguments based on the action

        Example usage:
            !chatbot enable - Enables the chatbot
            !chatbot disable - Disables the chatbot
            !chatbot status - Show chatbot status
            !chatbot clear - Clear conversation history in this channel
            !chatbot addchannel - Add current channel to chatbot channels
            !chatbot removechannel - Remove current channel from chatbot channels
            !chatbot diagnostics - Show diagnostic information
        """
        action = action.lower()

        if action == "enable":
            self.is_enabled = True
            await ctx.send("Chatbot has been enabled.")
            self.logger.info(f"{ctx.author} enabled the chatbot")

        elif action == "disable":
            self.is_enabled = False
            await ctx.send("Chatbot has been disabled.")
            self.logger.info(f"{ctx.author} disabled the chatbot")

        elif action == "status":
            status = "enabled" if self.is_enabled else "disabled"
            channels = [f"<#{channel_id}>" for channel_id in self.target_channels]
            channels_str = ", ".join(channels) if channels else "None"

            embed = discord.Embed(
                title="Chatbot Status",
                description=f"Current chatbot configuration",
                color=discord.Color.blue(),
            )

            embed.add_field(name="Status", value=status.title(), inline=True)
            embed.add_field(
                name="Max History", value=str(CHATBOT_MAX_HISTORY), inline=True
            )
            embed.add_field(
                name="Max Tokens", value=str(CHATBOT_MAX_TOKENS), inline=True
            )
            embed.add_field(name="Active Channels", value=channels_str, inline=False)

            await ctx.send(embed=embed)

        elif action == "clear":
            # Clear conversation history for the channel
            channel_key = f"channel:{ctx.channel.id}"
            guild_data = self.db.get_guild_settings(ctx.guild.id)

            if "chatbot" in guild_data and channel_key in guild_data["chatbot"]:
                guild_data["chatbot"][channel_key] = []
                self.db.save_guild_settings(ctx.guild.id, guild_data)
                await ctx.send(
                    "Conversation history has been cleared for this channel."
                )
                self.logger.info(
                    f"{ctx.author} cleared conversation history in {ctx.channel.name}"
                )
            else:
                await ctx.send(
                    "There's no conversation history to clear in this channel."
                )

        elif action == "addchannel":
            # Add current channel to the list of monitored channels
            if ctx.channel.id not in self.target_channels:
                self.target_channels.append(ctx.channel.id)
                await ctx.send(f"Added {ctx.channel.mention} to chatbot channels.")
                self.logger.info(
                    f"{ctx.author} added {ctx.channel.name} to chatbot channels"
                )
            else:
                await ctx.send(f"{ctx.channel.mention} is already a chatbot channel.")

        elif action == "removechannel":
            # Remove current channel from the list of monitored channels
            if ctx.channel.id in self.target_channels:
                self.target_channels.remove(ctx.channel.id)
                await ctx.send(f"Removed {ctx.channel.mention} from chatbot channels.")
                self.logger.info(
                    f"{ctx.author} removed {ctx.channel.name} from chatbot channels"
                )
            else:
                await ctx.send(f"{ctx.channel.mention} is not a chatbot channel.")

        elif action == "diagnostics":
            # Display diagnostic information
            last_active = self.stats.get("last_active", datetime.datetime.utcnow())
            time_since = (
                datetime.datetime.utcnow() - last_active
            ).total_seconds() / 60  # minutes

            embed = discord.Embed(
                title="Chatbot Diagnostics",
                description=f"Performance statistics and diagnostics",
                color=discord.Color.gold(),
            )

            embed.add_field(
                name="Messages",
                value=f"Received: {self.stats.get('messages_received', 0)}\nResponses: {self.stats.get('responses_sent', 0)}\nFailures: {self.stats.get('response_failures', 0)}",
                inline=False,
            )

            embed.add_field(
                name="Success Rate",
                value=f"{int((self.stats.get('responses_sent', 0) / max(1, self.stats.get('messages_received', 1))) * 100)}%",
                inline=True,
            )

            embed.add_field(
                name="Last Activity",
                value=(
                    f"{int(time_since)} minutes ago" if time_since > 1 else "Just now"
                ),
                inline=True,
            )

            embed.add_field(
                name="Active Channels",
                value=f"{len(self.target_channels)} configured",
                inline=True,
            )

            embed.add_field(
                name="User Data",
                value=f"{len(self.user_info)} users tracked",
                inline=True,
            )

            await ctx.send(embed=embed)

        else:
            await ctx.send(
                f"Unknown action: {action}\n"
                f"Valid actions are: enable, disable, status, clear, addchannel, removechannel, diagnostics"
            )


async def setup(bot: commands.Bot):
    """Add this cog to the bot."""
    await bot.add_cog(ChatbotCog(bot))

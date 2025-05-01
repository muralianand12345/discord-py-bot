"""
Chatbot functionality for Discord bot with friendly, conversational personality.
"""

import asyncio
import datetime
import logging
import random
import re
import traceback
from collections import deque
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
    CHATBOT_PERSONALITY,
    PROMPTS,
)


class ChatbotCog(commands.Cog, name="Chatbot"):
    """Friendly AI-powered chatbot for natural conversations in Discord channels."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger("chatbot_cog")
        self.llm = LLM()
        self.db = DatabaseManager()
        self.is_enabled = CHATBOT_ENABLED

        # Convert any string IDs to integers if needed
        self.target_channels = []
        for channel in CHATBOT_CHANNELS:
            if isinstance(channel, str) and channel.isdigit():
                self.target_channels.append(int(channel))
            elif isinstance(channel, int):
                self.target_channels.append(channel)

        self.logger.info(f"Chatbot initialized with channels: {self.target_channels}")

        # User interaction tracking
        self.typing_lock = {}  # Tracks channels where bot is "typing"
        self.recent_questions = {}  # Tracks recent questions to avoid repetition
        self.conversation_topics = {}  # Tracks topics per channel
        self.user_info = {}  # Stores user information for personalization
        self.recent_interactions = {}  # Tracks channel activity recency

        # Recent messages queue per channel (for quick access without DB)
        self.message_queue = {}

        # Personality traits - adjustable based on CHATBOT_PERSONALITY setting
        self.personality = {
            "friendliness": 0.9,  # Very friendly
            "humor": 0.7,  # Moderately humorous
            "helpfulness": 0.8,  # Quite helpful
            "chattiness": 0.7,  # Moderately chatty
            "formality": 0.3,  # Informal
        }

        # Parsing personality traits
        if CHATBOT_PERSONALITY:
            traits = CHATBOT_PERSONALITY.lower().split(",")
            for trait in traits:
                trait = trait.strip()
                if "friendly" in trait:
                    self.personality["friendliness"] = 0.9
                if "helpful" in trait:
                    self.personality["helpfulness"] = 0.9
                if "humor" in trait or "funny" in trait:
                    self.personality["humor"] = 0.8
                if "meme" in trait:
                    self.personality["humor"] = 0.9
                    self.personality["formality"] = 0.2
                if "formal" in trait:
                    self.personality["formality"] = 0.7

        # Statistics for monitoring
        self.stats = {
            "messages_received": 0,
            "responses_sent": 0,
            "response_failures": 0,
            "last_active": datetime.datetime.utcnow(),
        }

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle incoming messages for the chatbot with friendly personality."""
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

            # Log the incoming message
            self.logger.info(
                f"Received message from {message.author.display_name}: '{content}'"
            )

            # Store user info for personalization
            self._update_user_info(message.author)

            # Add message to queue for this channel
            channel_id = message.channel.id
            if channel_id not in self.message_queue:
                self.message_queue[channel_id] = deque(maxlen=10)

            self.message_queue[channel_id].append(
                {
                    "author": message.author.display_name,
                    "author_id": message.author.id,
                    "content": content,
                    "timestamp": datetime.datetime.utcnow(),
                }
            )

            # Mark channel as recently active
            self.recent_interactions[channel_id] = datetime.datetime.utcnow()

            # Check if message is a repeat
            is_repeat = self._check_repeated_question(
                message.channel.id, message.author.id, content
            )

            # Calculate if we should respond
            should_respond = self._should_respond(message.channel.id, message, content)

            if not should_respond:
                self.logger.info(
                    f"Decided not to respond to {message.author.display_name}'s message"
                )
                return

            # Start typing indicator with variable duration based on message complexity
            typing_duration = min(
                1.2 + (len(content) * 0.008),
                2.5,  # Slightly faster response time for friendly bot
            )
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

                # Generate the response with retry logic
                response = await self._generate_friendly_response(
                    conversation_history, message.author, is_repeat
                )

                # Clean the response
                response = self._clean_response(response, conversation_history)

                # Add the bot's response to history
                current_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                conversation_history.append(
                    {
                        "role": "assistant",
                        "username": CHATBOT_NAME,
                        "content": response,
                        "timestamp": current_time,
                        "user_id": self.bot.user.id,
                        "channel_id": message.channel.id,
                    }
                )

                # Save the updated conversation history
                await self._save_channel_history(
                    message.channel.id, conversation_history
                )

                # Add a small, natural-feeling delay before responding
                delay = random.uniform(0.3, 0.7)  # Slightly faster for friendly vibes
                await asyncio.sleep(delay)

                # Send the message
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
                    try:
                        # Simplified fallback
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
                self.logger.error(f"Error in message handling: {str(e)}")
                self.logger.error(traceback.format_exc())
                self.stats["response_failures"] += 1

                # Friendly error message
                try:
                    await message.channel.send(
                        "Whoops, I got distracted for a second there! What were we talking about?"
                    )
                except:
                    pass

            finally:
                # Always stop typing indicator
                await self._set_typing(message.channel, False)

    def _should_respond(
        self, channel_id: int, message: discord.Message, content: str
    ) -> bool:
        """
        Determine whether to respond to a message with friendly personality influence.

        Args:
            channel_id: The channel ID
            message: The message object
            content: The message content

        Returns:
            Boolean indicating whether to respond
        """
        # Always respond to direct questions or bot mentions
        if re.search(r"\?$", content) or re.search(
            r"\b(what|how|why|when|who|where|is|are|can|could|would|should|did)\b",
            content.lower(),
        ):
            return True

        # Always respond if mentioned directly
        bot_name_variations = [
            CHATBOT_NAME.lower(),
            "bot",
            self.bot.user.name.lower() if self.bot.user else "",
        ]

        if any(name in content.lower() for name in bot_name_variations if name):
            return True

        # Get recent messages for context
        recent_msgs = self._get_recent_messages(channel_id)

        # First message in channel - respond to kick things off
        if not recent_msgs:
            return True

        # Friendly bots respond to short greetings
        greeting_patterns = [
            r"\b(hi|hey|hello|sup|yo|hiya|howdy|greetings)\b",
            r"^(good morning|good afternoon|good evening)$",
        ]

        if any(re.search(pattern, content.lower()) for pattern in greeting_patterns):
            return True

        # Let's not respond if we just sent a message (avoid double-responses)
        if recent_msgs and recent_msgs[-1].get("user_id") == self.bot.user.id:
            # Check time since last bot message
            try:
                last_time = datetime.datetime.strptime(
                    recent_msgs[-1].get("timestamp", ""), "%Y-%m-%d %H:%M:%S"
                )
                current_time = datetime.datetime.utcnow()
                time_diff = (current_time - last_time).total_seconds()

                # If very recent and not a direct question/mention, don't respond
                if time_diff < 8:  # Slightly shorter wait time for friendly bot
                    return False
            except ValueError:
                pass

        # Friendly bots have higher response rates, influenced by personality settings
        # Base chance + influence from the friendliness/chattiness settings
        base_chance = 0.5
        friendliness_factor = self.personality["friendliness"] * 0.3  # Up to 0.3 bonus
        chattiness_factor = self.personality["chattiness"] * 0.2  # Up to 0.2 bonus

        response_chance = base_chance + friendliness_factor + chattiness_factor

        # Additional bonus for short messages which are easier to respond to
        if len(content) < 15:
            response_chance += 0.15

        # Gentle decay for very inactive channels
        if channel_id in self.recent_interactions:
            last_interaction = self.recent_interactions[channel_id]
            hours_since = (
                datetime.datetime.utcnow() - last_interaction
            ).total_seconds() / 3600

            if hours_since > 12:  # Been quiet for over 12 hours
                response_chance += 0.2  # More likely to respond to revive conversation

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
                "interaction_count": 0,
                "last_interaction": datetime.datetime.utcnow(),
            }
        else:
            # Update existing user info
            self.user_info[user.id]["interaction_count"] += 1
            self.user_info[user.id]["last_interaction"] = datetime.datetime.utcnow()
            self.user_info[user.id]["roles"] = [
                role.name for role in user.roles if role.name != "@everyone"
            ]

    def _update_conversation_topics(self, channel_id: int, content: str):
        """
        Extract and track conversation topics for context awareness.

        Args:
            channel_id: The channel ID
            content: The message content
        """
        if channel_id not in self.conversation_topics:
            self.conversation_topics[channel_id] = set()

        # Simple keyword extraction
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
            "because",
            "these",
            "those",
            "some",
            "such",
            "only",
            "will",
            "shall",
            "myself",
            "yourself",
            "itself",
            "things",
        }

        topics = [word for word in words if word not in stop_words]

        # Add to conversation topics, limiting to 10 most recent
        self.conversation_topics[channel_id].update(topics)
        if len(self.conversation_topics[channel_id]) > 10:
            # Convert to list to remove random elements
            topics_list = list(self.conversation_topics[channel_id])
            self.conversation_topics[channel_id] = set(topics_list[-10:])

    async def _generate_friendly_response(
        self,
        conversation_history: List[Dict],
        user: discord.Member,
        is_repeat: bool = False,
    ) -> str:
        """
        Generate a friendly response with retry logic.

        Args:
            conversation_history: The conversation history
            user: The Discord user
            is_repeat: Whether it's a repeated question

        Returns:
            Generated response text
        """
        if not conversation_history:
            return "Hi there! How can I help you today?"

        current_message = conversation_history[-1]["content"]
        current_user = conversation_history[-1]["username"]
        user_id = conversation_history[-1]["user_id"]

        # Format the conversation history
        formatted_history = self._format_conversation_history(conversation_history)

        # Get basic system message
        system_message = PROMPTS["chatbot"]["system_message"]

        # Build context with Discord formatting information and friendly personality
        context = self._build_friendly_context(conversation_history, user, is_repeat)

        # Additional Discord formatting guidance
        discord_formatting = f"""
        IMPORTANT DISCORD FORMATTING INSTRUCTIONS:
        
        1. When referring to users, use <@{user_id}> to mention them
        2. When referring to timestamps, use Discord timestamp format: <t:{int(datetime.datetime.utcnow().timestamp())}:R>
        3. Use **bold** for emphasis, *italics* for subtle emphasis, and `code` for tech terms
        4. Remember to be warm, friendly, and conversational - you're a fun bot to chat with!
        5. Avoid overly long responses - be concise but helpful
        """

        # Create the LLM message payload with friendly, personalized approach
        messages = [
            {"role": "system", "content": system_message},
            {"role": "system", "content": context},
            {"role": "system", "content": discord_formatting},
        ]

        # Add conversation history for context
        if formatted_history:
            messages.append(
                {
                    "role": "system",
                    "content": f"Recent conversation:\n{formatted_history}",
                }
            )

        # Add the current message as the last user message
        messages.append(
            {"role": "user", "content": f"{current_user} said: {current_message}"}
        )

        # Retry mechanism with backoff
        max_retries = 2
        response = None

        for attempt in range(max_retries + 1):
            try:
                response = await self.llm.invoke(
                    messages, max_tokens=CHATBOT_MAX_TOKENS
                )

                if self._is_valid_friendly_response(response, current_message):
                    break

                if attempt < max_retries:
                    self.logger.warning(f"Generated invalid response, retrying...")
                    await asyncio.sleep(0.3)
                else:
                    response = self._get_friendly_fallback(current_message)

            except Exception as e:
                self.logger.error(f"LLM error on attempt {attempt+1}: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(0.5)
                else:
                    response = self._get_friendly_fallback(current_message)

        # Ensure we have a valid response
        if not response:
            response = self._get_friendly_fallback(current_message)

        return response

    def _is_valid_friendly_response(self, response: str, user_message: str) -> bool:
        """
        Check if response is valid and friendly.

        Args:
            response: The generated response
            user_message: The user's message

        Returns:
            Whether the response is valid
        """
        if not response or len(response.strip()) < 2:
            return False

        # Avoid pure repetition
        if len(user_message) > 5:
            similarity = self._calculate_similarity(response, user_message)
            if similarity > 0.8:
                return False

        # Check for problematic phrasings that make the bot sound too robotic
        bot_phrases = [
            "I'm an AI",
            "As an AI",
            "I don't have personal",
            "I cannot access",
            "I don't have the ability to",
            "I cannot browse",
            "my knowledge cutoff",
            "my training data",
            "I'm just a language model",
            "I don't have access to",
            "I'm not able to",
        ]

        if any(phrase.lower() in response.lower() for phrase in bot_phrases):
            return False

        return True

    def _get_friendly_fallback(self, user_message: str) -> str:
        """
        Get a friendly fallback response when generation fails.

        Args:
            user_message: The user's message

        Returns:
            Fallback response
        """
        # Check message type for appropriate fallback

        # For greetings
        if re.search(r"\b(hi|hey|hello|sup|yo|hiya|howdy)\b", user_message.lower()):
            greetings = [
                "Hey there! How's it going?",
                "Hi! What's up?",
                "Hello! How are you doing today?",
                "Hey! Nice to chat with you! What's new?",
                "Hi there! How's your day going?",
            ]
            return random.choice(greetings)

        # For questions
        if "?" in user_message or re.search(
            r"\b(what|how|why|when|who|where)\b", user_message.lower()
        ):
            question_responses = [
                "That's an interesting question! What do you think?",
                "I've been wondering about that too. Any thoughts?",
                "Hmm, let me think about that... What's your take on it?",
                "That's a good question! I'd love to hear your perspective.",
                "I'm curious about that too. What do you think about it?",
            ]
            return random.choice(question_responses)

        # For short messages that might be reactions
        if len(user_message) < 10:
            short_responses = [
                "Cool! What else is on your mind?",
                "Nice! How's your day going?",
                "Awesome! What else is new?",
                "I hear you! Anything else you want to chat about?",
                "For sure! What's been keeping you busy lately?",
            ]
            return random.choice(short_responses)

        # General fallbacks
        general_fallbacks = [
            "That's interesting! Tell me more about what you think?",
            "I'd love to hear more about that. What else is on your mind?",
            "Cool! How's your day going so far?",
            "I see what you mean. What else have you been up to lately?",
            "Totally get that. What else is happening in your world?",
            "I hear you! What's been the highlight of your day so far?",
        ]
        return random.choice(general_fallbacks)

    def _build_friendly_context(
        self, conversation_history: List[Dict], user: discord.Member, is_repeat: bool
    ) -> str:
        """
        Build enhanced context with friendly personality.

        Args:
            conversation_history: List of conversation messages
            user: The Discord user
            is_repeat: Whether the message is a repeat

        Returns:
            Enhanced context string
        """
        context_parts = []

        # Add conversation participants
        active_users = self._get_active_users(conversation_history)
        if active_users:
            context_parts.append(
                f"You're having a friendly chat with: {', '.join(active_users)}.\n"
            )

        # Add current user info with ID for mentions
        context_parts.append(
            f"You're currently talking to {user.display_name} (user ID: {user.id}). "
            f"To mention them, use: <@{user.id}>\n"
        )

        # Add interaction history if available
        if user.id in self.user_info:
            interaction_count = self.user_info[user.id].get("interaction_count", 0)
            if interaction_count > 5:
                context_parts.append(
                    f"You've chatted with {user.display_name} many times before, you're friendly with them.\n"
                )

        # Discord formatting with current timestamp
        current_timestamp = int(datetime.datetime.utcnow().timestamp())
        context_parts.append(
            f"Current timestamp: {current_timestamp}. "
            f"You can use Discord timestamp format like <t:{current_timestamp}:R> for relative time.\n"
        )

        # Add recent conversation topics if available
        channel_id = (
            conversation_history[-1].get("channel_id") if conversation_history else None
        )
        if (
            channel_id
            and channel_id in self.conversation_topics
            and self.conversation_topics[channel_id]
        ):
            topics = ", ".join(self.conversation_topics[channel_id])
            context_parts.append(f"Topics you've been discussing: {topics}.\n")

        # Special handling for repeated questions
        if is_repeat:
            context_parts.append(
                "Note: The user is asking something similar to what they asked before. "
                "Try to give a different perspective or more information this time.\n"
            )

        # Friendly personality guidance - varies based on personality settings
        personality_guidance = f"""
        Your personality:
        - You're very friendly and warm{" with a good sense of humor" if self.personality["humor"] > 0.5 else ""}
        - You use {"informal" if self.personality["formality"] < 0.5 else "somewhat formal"} language
        - You're genuinely interested in what people have to say
        - You respond with {"short, concise" if self.personality["chattiness"] < 0.5 else "engaging but not too long"} messages
        - You're helpful but never preachy or lecturing
        - You {"occasionally use emojis for expression" if self.personality["formality"] < 0.6 else "use minimal emojis"}
        
        Remember: You're a friendly chat companion, not a search engine or news source.
        Focus on having a natural conversation rather than just providing information.
        """

        context_parts.append(personality_guidance)

        return "\n".join(context_parts)

    def _get_active_users(self, conversation_history: List[Dict]) -> List[str]:
        """
        Extract unique active users from recent conversation history.

        Args:
            conversation_history: List of conversation messages

        Returns:
            List of active usernames
        """
        # Get recent messages
        recent_history = (
            conversation_history[-8:]
            if len(conversation_history) > 8
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
        Format conversation history for the LLM prompt.

        Args:
            history: List of conversation messages

        Returns:
            Formatted conversation history text
        """
        # Skip the last message as it will be added separately
        if len(history) <= 1:
            return ""

        # Take recent messages for context (last 8)
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

    def _clean_response(self, response: str, conversation_history: List[Dict]) -> str:
        """
        Clean response for better readability and authenticity.

        Args:
            response: The response text
            conversation_history: The conversation history

        Returns:
            Cleaned response
        """
        if not response:
            return "Hey there! What's up?"

        # Remove any bot name self-referential prefixes
        response = re.sub(r"^(\*\*)?Bot:(\*\*)?\s*", "", response)
        response = re.sub(r"^(\*\*)?Assistant:(\*\*)?\s*", "", response)
        if CHATBOT_NAME:
            response = re.sub(rf"^(\*\*)?{CHATBOT_NAME}:(\*\*)?\s*", "", response)

        # Check for response similarity to avoid repetition
        recent_bot_responses = [
            msg.get("content", "")
            for msg in conversation_history[-10:]
            if msg.get("role") == "assistant" and msg.get("user_id") == self.bot.user.id
        ]

        for past_msg in recent_bot_responses:
            if (
                past_msg
                and response
                and self._calculate_similarity(response, past_msg) > 0.7
            ):
                # Add a conversation refresher if too similar
                conversation_refreshers = [
                    "\n\nAnyway, what's new with you?",
                    "\n\nHow about you? What's on your mind?",
                    "\n\nBut enough about that - how's your day going?",
                    "\n\nWhat about you? Any fun plans coming up?",
                    "\n\nBy the way, what have you been up to lately?",
                ]
                return response + random.choice(conversation_refreshers)

        return response

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity between two strings.

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

    def _smart_chunk_message(self, message: str, max_length: int = 1500) -> List[str]:
        """
        Intelligently split long messages at natural breaking points.

        Args:
            message: The message to split
            max_length: Maximum length per chunk

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
        Get recent messages from a channel.

        Args:
            channel_id: ID of the Discord channel

        Returns:
            List of recent messages
        """
        # Check if we have messages in the queue first (faster)
        if channel_id in self.message_queue and self.message_queue[channel_id]:
            return list(self.message_queue[channel_id])

        # If not in queue, get from database
        guild_data = self.db.get_guild_settings(channel_id)
        channel_key = f"channel:{channel_id}"

        # Return empty list if no history
        if "chatbot" not in guild_data or channel_key not in guild_data["chatbot"]:
            return []

        # Get conversation history
        return guild_data["chatbot"].get(channel_key, [])

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
        self, channel: discord.TextChannel, is_typing: bool, duration: float = 2.0
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
            action: Action to perform (enable, disable, status, etc.)
            args: Additional arguments based on the action
        """
        action = action.lower()

        if action == "enable":
            self.is_enabled = True
            await ctx.send("🎉 Chatbot has been enabled. I'm ready to chat!")
            self.logger.info(f"{ctx.author} enabled the chatbot")

        elif action == "disable":
            self.is_enabled = False
            await ctx.send("Chatbot has been disabled. I'll be quiet now.")
            self.logger.info(f"{ctx.author} disabled the chatbot")

        elif action == "status":
            status = "enabled" if self.is_enabled else "disabled"
            channels = [f"<#{channel_id}>" for channel_id in self.target_channels]
            channels_str = ", ".join(channels) if channels else "None"

            embed = discord.Embed(
                title="🤖 Chatbot Status",
                description=f"Current chatbot configuration",
                color=discord.Color.blue(),
            )

            embed.add_field(name="Status", value=status.title(), inline=True)
            embed.add_field(name="Personality", value=CHATBOT_PERSONALITY, inline=True)
            embed.add_field(
                name="Memory Size", value=str(CHATBOT_MAX_HISTORY), inline=True
            )
            embed.add_field(name="Active Channels", value=channels_str, inline=False)

            # Add interaction stats
            embed.add_field(
                name="Statistics",
                value=f"Messages received: {self.stats['messages_received']}\nResponses sent: {self.stats['responses_sent']}",
                inline=False,
            )

            await ctx.send(embed=embed)

        elif action == "clear":
            # Clear conversation history for the channel
            channel_key = f"channel:{ctx.channel.id}"
            guild_data = self.db.get_guild_settings(ctx.guild.id)

            if "chatbot" in guild_data and channel_key in guild_data["chatbot"]:
                guild_data["chatbot"][channel_key] = []
                self.db.save_guild_settings(ctx.guild.id, guild_data)

                # Also clear memory queue
                if ctx.channel.id in self.message_queue:
                    self.message_queue[ctx.channel.id].clear()

                await ctx.send(
                    "🧹 Conversation history has been cleared for this channel!"
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
                await ctx.send(
                    f"✅ Added {ctx.channel.mention} to chatbot channels. I'll start chatting here!"
                )
                self.logger.info(
                    f"{ctx.author} added {ctx.channel.name} to chatbot channels"
                )
            else:
                await ctx.send(f"{ctx.channel.mention} is already a chatbot channel.")

        elif action == "removechannel":
            # Remove current channel from the list of monitored channels
            if ctx.channel.id in self.target_channels:
                self.target_channels.remove(ctx.channel.id)
                await ctx.send(
                    f"🔕 Removed {ctx.channel.mention} from chatbot channels. I'll no longer chat here."
                )
                self.logger.info(
                    f"{ctx.author} removed {ctx.channel.name} from chatbot channels"
                )
            else:
                await ctx.send(f"{ctx.channel.mention} is not a chatbot channel.")

        elif action == "personality":
            # Set the chatbot personality if arguments provided
            if not args:
                current_traits = ", ".join(
                    [
                        f"{trait}: {value:.1f}"
                        for trait, value in self.personality.items()
                    ]
                )
                await ctx.send(
                    f"Current personality traits:\n{current_traits}\n\nUse `{ctx.prefix}chatbot personality friendly` or similar to change."
                )
                return

            personality_type = args[0].lower()

            if personality_type == "friendly":
                self.personality = {
                    "friendliness": 0.9,
                    "humor": 0.7,
                    "helpfulness": 0.8,
                    "chattiness": 0.7,
                    "formality": 0.3,
                }
                await ctx.send("Personality set to friendly and approachable! 😊")

            elif personality_type == "helpful":
                self.personality = {
                    "friendliness": 0.7,
                    "humor": 0.4,
                    "helpfulness": 0.9,
                    "chattiness": 0.5,
                    "formality": 0.6,
                }
                await ctx.send("Personality set to more helpful and informative! 📚")

            elif personality_type == "funny":
                self.personality = {
                    "friendliness": 0.8,
                    "humor": 0.9,
                    "helpfulness": 0.6,
                    "chattiness": 0.8,
                    "formality": 0.2,
                }
                await ctx.send("Personality set to funny and entertaining! 😄")

            elif personality_type == "formal":
                self.personality = {
                    "friendliness": 0.6,
                    "humor": 0.3,
                    "helpfulness": 0.8,
                    "chattiness": 0.5,
                    "formality": 0.9,
                }
                await ctx.send("Personality set to more formal and professional.")

            else:
                await ctx.send(
                    f"Unknown personality type. Try: friendly, helpful, funny, or formal"
                )

        elif action == "test":
            # Quick test to verify the chatbot is working
            if not self.is_enabled:
                await ctx.send(
                    "⚠️ Chatbot is currently disabled. Enable it first with `!chatbot enable`"
                )
                return

            await ctx.send("🔍 Testing the chatbot response system...")

            try:
                test_message = "Hello there! How are you today?"
                if args and len(args) > 0:
                    test_message = " ".join(args)

                messages = [
                    {"role": "system", "content": "You are a friendly Discord bot."},
                    {"role": "user", "content": test_message},
                ]

                response = await self.llm.invoke(messages, max_tokens=100)
                await ctx.send(
                    f"✅ Test successful! Response to '{test_message}':\n\n{response}"
                )

            except Exception as e:
                await ctx.send(f"❌ Test failed: {str(e)}")
                self.logger.error(f"Chatbot test failed: {str(e)}")

        else:
            await ctx.send(
                f"Unknown action: `{action}`\n"
                f"Valid actions are: `enable`, `disable`, `status`, `clear`, `addchannel`, `removechannel`, `personality`, `test`"
            )


async def setup(bot: commands.Bot):
    """Add this cog to the bot."""
    await bot.add_cog(ChatbotCog(bot))

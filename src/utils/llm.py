"""
Enhanced LLM service handler with improved error handling and response processing.

This module provides a reliable wrapper around LLM APIs using the OpenAI client,
with proper error handling, rate limiting, and response processing.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Union, Any

# OpenAI client for API communication
from openai import AsyncOpenAI
from openai import OpenAI

# Local imports
from utils.settings import (
    GROQ_API_BASE,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_COOLDOWN_SECONDS,
    LLM_REQUEST_TIMEOUT,
    MAX_REQUESTS_PER_MINUTE,
)

logger = logging.getLogger("llm")


class LLM:
    """
    Enhanced language model interface for interacting with LLM APIs.
    Configured to work with Groq by default, but compatible with any OpenAI-compatible API.
    """

    # Class-level variables for rate limiting and clients
    _last_request_time = 0
    _lock = asyncio.Lock()
    _request_count = 0
    _request_reset_time = 0
    _async_client = None
    _sync_client = None

    # Track success/failure rates for monitoring
    _total_requests = 0
    _successful_requests = 0
    _failed_requests = 0
    _last_error = None

    def __init__(self) -> None:
        """Initialize the LLM service with OpenAI client configuration."""
        self.api_key = GROQ_API_KEY
        self.base_url = GROQ_API_BASE
        self.model = GROQ_MODEL

        # Message content fallbacks when API fails
        self.fallback_responses = [
            "I'm thinking about that...",
            "That's an interesting topic!",
            "I'd love to chat about that.",
            "Tell me more about what you think?",
            "I'm curious to hear your thoughts on this.",
            "That's a good point. What else is on your mind?",
        ]

    @classmethod
    def get_async_client(cls) -> AsyncOpenAI:
        """
        Get or create the async OpenAI client.

        Returns:
            AsyncOpenAI client instance
        """
        if cls._async_client is None:
            cls._async_client = AsyncOpenAI(
                api_key=GROQ_API_KEY,
                base_url=GROQ_API_BASE,
                timeout=LLM_REQUEST_TIMEOUT,
            )
        return cls._async_client

    @classmethod
    def get_sync_client(cls) -> OpenAI:
        """
        Get or create the synchronous OpenAI client.

        Returns:
            OpenAI client instance
        """
        if cls._sync_client is None:
            cls._sync_client = OpenAI(
                api_key=GROQ_API_KEY,
                base_url=GROQ_API_BASE,
                timeout=LLM_REQUEST_TIMEOUT,
            )
        return cls._sync_client

    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """
        Get current usage statistics and status.

        Returns:
            Dictionary with usage statistics
        """
        success_rate = 0
        if cls._total_requests > 0:
            success_rate = (cls._successful_requests / cls._total_requests) * 100

        return {
            "total_requests": cls._total_requests,
            "successful_requests": cls._successful_requests,
            "failed_requests": cls._failed_requests,
            "success_rate": f"{success_rate:.1f}%",
            "last_error": str(cls._last_error) if cls._last_error else None,
            "last_request_time": cls._last_request_time,
        }

    async def invoke(
        self, messages: List[Dict[str, str]], max_tokens: int = 150, **kwargs
    ) -> Optional[str]:
        """
        Invoke the LLM with a list of messages using AsyncOpenAI client.

        Note: Removed temperature parameter as it's not supported by Groq API.

        Args:
            messages: List of message objects with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters to pass to the API

        Returns:
            Generated text response or fallback if there's an error
        """
        if not self.api_key:
            logger.error("No API key available")
            raise ValueError("No API key available for LLM")

        # Wait for rate limiting if necessary
        await self._handle_rate_limiting()

        # Update request stats
        LLM._total_requests += 1

        try:
            # Get the async client
            client = self.get_async_client()

            # Remove temperature if present in kwargs (not supported by Groq)
            if "temperature" in kwargs:
                logger.warning(
                    "Temperature parameter removed (not supported by Groq API)"
                )
                kwargs.pop("temperature")

            # Create the chat completion
            response = await client.chat.completions.create(
                model=self.model, messages=messages, max_tokens=max_tokens, **kwargs
            )

            # Extract the content
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content.strip()

                # Update success stats
                LLM._successful_requests += 1

                return content
            else:
                logger.warning("Empty response from LLM API")
                LLM._failed_requests += 1
                return self._get_random_fallback()

        except Exception as e:
            logger.error(f"LLM request failed: {str(e)}")
            LLM._failed_requests += 1
            LLM._last_error = e

            # Return a fallback rather than raising the exception
            return self._get_random_fallback()

    def invoke_sync(
        self, messages: List[Dict[str, str]], max_tokens: int = 150, **kwargs
    ) -> Optional[str]:
        """
        Invoke the LLM with synchronous client (useful for non-async contexts).

        Args:
            messages: List of message objects with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters to pass to the API

        Returns:
            Generated text response or fallback if there's an error
        """
        if not self.api_key:
            logger.error("No API key available")
            raise ValueError("No API key available for LLM")

        # Update request stats
        LLM._total_requests += 1

        try:
            # Get the synchronous client
            client = self.get_sync_client()

            # Remove temperature if present in kwargs
            if "temperature" in kwargs:
                logger.warning(
                    "Temperature parameter removed (not supported by Groq API)"
                )
                kwargs.pop("temperature")

            # Create the chat completion
            response = client.chat.completions.create(
                model=self.model, messages=messages, max_tokens=max_tokens, **kwargs
            )

            # Extract the content
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content.strip()

                # Update success stats
                LLM._successful_requests += 1

                return content
            else:
                logger.warning("Empty response from LLM API")
                LLM._failed_requests += 1
                return self._get_random_fallback()

        except Exception as e:
            logger.error(f"Sync LLM request failed: {str(e)}")
            LLM._failed_requests += 1
            LLM._last_error = e

            # Return a fallback rather than raising the exception
            return self._get_random_fallback()

    async def _handle_rate_limiting(self) -> None:
        """
        Handle rate limiting logic with backoff strategy.

        Ensures we don't exceed the maximum requests per minute
        and enforces a cooldown between requests.
        """
        async with LLM._lock:
            # Handle rate limiting
            current_time = time.time()

            # Reset counter if a minute has passed
            if current_time - LLM._request_reset_time >= 60:
                LLM._request_count = 0
                LLM._request_reset_time = current_time

            # Check if we're at the rate limit
            if LLM._request_count >= MAX_REQUESTS_PER_MINUTE:
                # Wait until we can make a request
                wait_time = 60 - (current_time - LLM._request_reset_time)
                if wait_time > 0:
                    logger.warning(f"Rate limit reached. Waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    LLM._request_count = 0
                    LLM._request_reset_time = time.time()

            # Enforce cooldown between individual requests
            elapsed = current_time - LLM._last_request_time
            if elapsed < LLM_COOLDOWN_SECONDS:
                await asyncio.sleep(LLM_COOLDOWN_SECONDS - elapsed)

            # Update last request time and increment counter
            LLM._last_request_time = time.time()
            LLM._request_count += 1

    def _get_random_fallback(self) -> str:
        """
        Get a random fallback response when the API fails.

        Returns:
            Fallback response string
        """
        import random

        return random.choice(self.fallback_responses)

    @staticmethod
    async def extract_entities(text: str) -> Dict[str, List[str]]:
        """
        Extract entities like names, locations, etc. from text.

        Args:
            text: Text to extract entities from

        Returns:
            Dictionary with entity categories and values
        """
        # This is a placeholder for future expansion
        # In a real implementation, we would use the LLM for entity extraction
        entities = {
            "names": [],
            "locations": [],
            "topics": [],
        }

        # For now, just return empty categories
        return entities

    @staticmethod
    async def classify_intent(text: str) -> str:
        """
        Classify the intent of a text message.

        Args:
            text: Text to classify

        Returns:
            Intent classification (greeting, question, statement, etc.)
        """
        # Simple patterns for basic intent recognition
        import re

        text_lower = text.lower()

        # Check for greetings
        if re.search(r"^(hi|hello|hey|greetings|howdy|yo|sup)\b", text_lower):
            return "greeting"

        # Check for questions
        if "?" in text or re.search(
            r"\b(what|how|why|when|who|where|is|are|can|could|would|should|did)\b",
            text_lower,
        ):
            return "question"

        # Check for gratitude
        if re.search(r"\b(thanks|thank you|thx|ty)\b", text_lower):
            return "gratitude"

        # Check for farewells
        if re.search(
            r"\b(bye|goodbye|see you|later|goodnight|good night)\b", text_lower
        ):
            return "farewell"

        # Default
        return "statement"

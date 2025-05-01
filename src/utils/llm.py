"""
LLM service handler for integrating with language models.

This module provides a wrapper around LLM APIs using the OpenAI client,
with proper error handling and rate limiting.
"""

import asyncio
import logging
import time
from openai import AsyncOpenAI
from openai import OpenAI
from typing import Dict, List, Optional

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
    Language model interface for interacting with LLM APIs using OpenAI client.
    Configured to work with Groq by default, but can be used with any OpenAI-compatible API.
    """

    # Class-level variables for rate limiting
    _last_request_time = 0
    _lock = asyncio.Lock()
    _request_count = 0
    _request_reset_time = 0
    _async_client = None
    _sync_client = None

    def __init__(self) -> None:
        """Initialize the LLM service with OpenAI client."""
        self.api_key = GROQ_API_KEY
        self.base_url = GROQ_API_BASE
        self.model = GROQ_MODEL

    @classmethod
    def get_async_client(cls):
        """Get or create the async OpenAI client."""
        if cls._async_client is None:
            cls._async_client = AsyncOpenAI(
                api_key=GROQ_API_KEY,
                base_url=GROQ_API_BASE,
                timeout=LLM_REQUEST_TIMEOUT,
            )
        return cls._async_client

    @classmethod
    def get_sync_client(cls):
        """Get or create the synchronous OpenAI client."""
        if cls._sync_client is None:
            cls._sync_client = OpenAI(
                api_key=GROQ_API_KEY,
                base_url=GROQ_API_BASE,
                timeout=LLM_REQUEST_TIMEOUT,
            )
        return cls._sync_client

    async def invoke(
        self, messages: List[Dict[str, str]], max_tokens: int = 150, **kwargs
    ) -> Optional[str]:
        """
        Invoke the LLM with a list of messages using AsyncOpenAI client.

        Note: Removed temperature parameter as it's not supported by Groq API.

        Args:
            messages: List of message objects with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters to pass to the API (except temperature)

        Returns:
            Generated text response or None if there's an error
        """
        if not self.api_key:
            logger.error("No API key available")
            raise ValueError("No API key available")

        # Wait for rate limiting if necessary
        await self._handle_rate_limiting()

        try:
            # Get the async client
            client = self.get_async_client()

            # Remove temperature if present in kwargs
            if "temperature" in kwargs:
                logger.warning(
                    "Temperature parameter not supported by Groq API, removing"
                )
                kwargs.pop("temperature")

            # Create the chat completion
            response = await client.chat.completions.create(
                model=self.model, messages=messages, max_tokens=max_tokens, **kwargs
            )

            # Extract and return the content
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content.strip()
            else:
                logger.warning("Empty response from LLM")
                return None

        except Exception as e:
            logger.error(f"LLM request failed: {str(e)}")
            raise

    def invoke_sync(
        self, messages: List[Dict[str, str]], max_tokens: int = 150, **kwargs
    ) -> Optional[str]:
        """
        Invoke the LLM with a list of messages using synchronous OpenAI client.

        Note: Removed temperature parameter as it's not supported by Groq API.

        Args:
            messages: List of message objects with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters to pass to the API (except temperature)

        Returns:
            Generated text response or None if there's an error
        """
        if not self.api_key:
            logger.error("No API key available")
            raise ValueError("No API key available")

        try:
            # Get the synchronous client
            client = self.get_sync_client()

            # Remove temperature if present in kwargs
            if "temperature" in kwargs:
                logger.warning(
                    "Temperature parameter not supported by Groq API, removing"
                )
                kwargs.pop("temperature")

            # Create the chat completion
            response = client.chat.completions.create(
                model=self.model, messages=messages, max_tokens=max_tokens, **kwargs
            )

            # Extract and return the content
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content.strip()
            else:
                logger.warning("Empty response from LLM")
                return None

        except Exception as e:
            logger.error(f"LLM request failed: {str(e)}")
            raise

    async def _handle_rate_limiting(self) -> None:
        """
        Handle rate limiting logic.

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

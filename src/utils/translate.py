"""
Utility class for translating text using Groq LLM API.
"""

import json
import time
import logging
import aiohttp
import asyncio
from typing import Optional, List
from collections import OrderedDict

from utils.settings import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_API_BASE,
    TRANSLATION_CACHE_SIZE,
    TRANSLATION_COOLDOWN_SECONDS,
    MAX_TRANSLATION_LENGTH,
    MAX_REQUESTS_PER_MINUTE,
    USE_ROMANIZATION_FALLBACK,
)

logger = logging.getLogger("translation")


class LRUCache:
    """
    A simple Least Recently Used (LRU) cache implementation.

    Attributes:
        capacity: Maximum number of items the cache can hold
        cache: OrderedDict storing cached items
    """

    def __init__(self, capacity: int):
        """
        Initialize the LRU cache.

        Args:
            capacity: Maximum number of items the cache can hold
        """
        self.capacity = max(1, capacity)  # Ensure at least capacity 1
        self.cache = OrderedDict()

    def get(self, key: str) -> Optional[str]:
        """
        Get a value from the cache by key.

        Args:
            key: The key to look up

        Returns:
            The cached value or None if not found
        """
        if key not in self.cache:
            return None

        # Move the accessed item to the end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: str) -> None:
        """
        Add or update a value in the cache.

        Args:
            key: The key to store the value under
            value: The value to store
        """
        # If key exists, update its position
        if key in self.cache:
            self.cache.move_to_end(key)

        self.cache[key] = value

        # Remove oldest item if capacity exceeded
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)


class RateLimiter:
    """
    Rate limiter to prevent API overload.

    Attributes:
        max_requests: Maximum number of requests allowed in the time window
        time_window: Time window in seconds
        request_timestamps: List of timestamp records
    """

    def __init__(self, max_requests: int = 60, time_window: int = 60):
        """
        Initialize the rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in the time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_timestamps: List[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """
        Try to acquire permission to make a request.

        Returns:
            True if the request is allowed, False if it should be rate limited
        """
        async with self._lock:
            current_time = time.time()

            # Remove timestamps outside the current window
            self.request_timestamps = [
                ts
                for ts in self.request_timestamps
                if current_time - ts <= self.time_window
            ]

            # Check if we can make a new request
            if len(self.request_timestamps) < self.max_requests:
                self.request_timestamps.append(current_time)
                return True

            # Calculate wait time until the next slot becomes available
            if self.request_timestamps:
                wait_time = self.time_window - (
                    current_time - self.request_timestamps[0]
                )
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached. Need to wait {wait_time:.2f} seconds"
                    )
                return False

            return True

    async def wait_for_capacity(self) -> None:
        """
        Wait until a request slot becomes available.
        """
        while True:
            if await self.acquire():
                return

            # Wait a bit before checking again
            await asyncio.sleep(0.5)


class Translate:
    """
    Utility class for translating text to different languages using Groq LLM.
    """

    # Class-level cache for translations
    _translation_cache = LRUCache(TRANSLATION_CACHE_SIZE)

    # Rate limiter for the API
    _rate_limiter = RateLimiter(MAX_REQUESTS_PER_MINUTE, 60)

    # Class-level cooldown tracking
    _last_request_time = 0
    _lock = asyncio.Lock()

    @staticmethod
    async def to_japanese(text: str) -> str:
        """
        Translate text to Japanese using Groq LLM.

        Args:
            text: The text to translate

        Returns:
            Translated Japanese text
        """
        # Truncate input if too long
        if len(text) > MAX_TRANSLATION_LENGTH:
            logger.warning(
                f"Input text too long ({len(text)} chars), truncating to {MAX_TRANSLATION_LENGTH}"
            )
            text = text[:MAX_TRANSLATION_LENGTH]

        # Check cache first
        cached_result = Translate._translation_cache.get(f"ja:{text}")
        if cached_result:
            logger.debug(f"Cache hit for '{text}'")
            return cached_result

        # Enforce cooldown between requests
        async with Translate._lock:
            current_time = time.time()
            elapsed = current_time - Translate._last_request_time

            if elapsed < TRANSLATION_COOLDOWN_SECONDS:
                sleep_time = TRANSLATION_COOLDOWN_SECONDS - elapsed
                logger.debug(f"Cooldown: waiting {sleep_time:.2f}s between requests")
                await asyncio.sleep(sleep_time)

            # Update last request time
            Translate._last_request_time = time.time()

        # Wait for rate limiter capacity
        await Translate._rate_limiter.wait_for_capacity()

        try:
            result = await Translate._translate_with_groq(text, "ja")

            # Cache the result
            Translate._translation_cache.put(f"ja:{text}", result)

            return result
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")

            # Fall back to romanization if enabled
            if USE_ROMANIZATION_FALLBACK:
                logger.info("Falling back to romanization")
                return await Translate._romanize_to_japanese(text)
            return text

    @staticmethod
    async def _translate_with_groq(text: str, target_language: str) -> str:
        """
        Translate text using the Groq LLM API.

        Args:
            text: The text to translate
            target_language: Target language code (e.g., 'ja' for Japanese)

        Returns:
            Translated text

        Raises:
            Exception: If translation fails
        """
        if not GROQ_API_KEY:
            logger.warning("No GROQ_API_KEY found, falling back to romanization")
            if target_language == "ja":
                return await Translate._romanize_to_japanese(text)
            return text

        try:
            # Construct the completion endpoint
            endpoint = f"{GROQ_API_BASE}/chat/completions"

            # Prepare messages for the LLM
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are a translator specialized in translating names to {target_language}. "
                        "Your task is to translate the input text to the target language. "
                        "Respond with ONLY the translated text, without any additional explanation or comments."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Translate this name to {target_language}: {text}",
                },
            ]

            # Prepare the request payload
            payload = {
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": 0.2,  # Low temperature for more consistent translations
                "max_tokens": 150,
            }

            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint, json=payload, headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"Groq API error (status {response.status}): {error_text}"
                        )
                        raise Exception(f"API error: {response.status}")

                    data = await response.json()

                    # Extract the response
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"].strip()
                        return content
                    else:
                        logger.error(f"Unexpected API response: {data}")
                        raise Exception("Invalid API response format")

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error during translation: {str(e)}")
            raise Exception(f"HTTP error: {str(e)}")
        except asyncio.TimeoutError:
            logger.error("Translation request timed out")
            raise Exception("Request timed out")
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON response")
            raise Exception("Invalid JSON response")
        except Exception as e:
            logger.error(f"Unexpected error during translation: {str(e)}")
            raise

    @staticmethod
    async def translate_text(text: str, target_language: str) -> str:
        """
        Translate text to a specified target language.

        Args:
            text: The text to translate
            target_language: Target language code (e.g., 'ja' for Japanese)

        Returns:
            Translated text
        """
        # For Japanese, use the specialized method
        if target_language == "ja":
            return await Translate.to_japanese(text)

        # For other languages, use the general translation method
        # Check cache first
        cached_result = Translate._translation_cache.get(f"{target_language}:{text}")
        if cached_result:
            return cached_result

        try:
            result = await Translate._translate_with_groq(text, target_language)

            # Cache the result
            Translate._translation_cache.put(f"{target_language}:{text}", result)

            return result
        except Exception as e:
            logger.error(f"Translation to {target_language} failed: {str(e)}")
            # Return the original text on failure
            return text

    @staticmethod
    async def _romanize_to_japanese(text: str) -> str:
        """
        Simple fallback method to create a Japanese-like version of text.
        This is used when no translation API is available.

        Args:
            text: The text to romanize

        Returns:
            Japanese-like text
        """
        # Simple mapping of English characters to Japanese-like sounds
        romanization_map = {
            "a": "あ",
            "i": "い",
            "u": "う",
            "e": "え",
            "o": "お",
            "ka": "か",
            "ki": "き",
            "ku": "く",
            "ke": "け",
            "ko": "こ",
            "sa": "さ",
            "shi": "し",
            "su": "す",
            "se": "せ",
            "so": "そ",
            "ta": "た",
            "chi": "ち",
            "tsu": "つ",
            "te": "て",
            "to": "と",
            "na": "な",
            "ni": "に",
            "nu": "ぬ",
            "ne": "ね",
            "no": "の",
            "ha": "は",
            "hi": "ひ",
            "fu": "ふ",
            "he": "へ",
            "ho": "ほ",
            "ma": "ま",
            "mi": "み",
            "mu": "む",
            "me": "め",
            "mo": "も",
            "ya": "や",
            "yu": "ゆ",
            "yo": "よ",
            "ra": "ら",
            "ri": "り",
            "ru": "る",
            "re": "れ",
            "ro": "ろ",
            "wa": "わ",
            "wo": "を",
            "n": "ん",
            "ga": "が",
            "gi": "ぎ",
            "gu": "ぐ",
            "ge": "げ",
            "go": "ご",
            "za": "ざ",
            "ji": "じ",
            "zu": "ず",
            "ze": "ぜ",
            "zo": "ぞ",
            "da": "だ",
            "di": "ぢ",
            "du": "づ",
            "de": "で",
            "do": "ど",
            "ba": "ば",
            "bi": "び",
            "bu": "ぶ",
            "be": "べ",
            "bo": "ぼ",
            "pa": "ぱ",
            "pi": "ぴ",
            "pu": "ぷ",
            "pe": "ぺ",
            "po": "ぽ",
            "kya": "きゃ",
            "kyu": "きゅ",
            "kyo": "きょ",
            "sha": "しゃ",
            "shu": "しゅ",
            "sho": "しょ",
            "cha": "ちゃ",
            "chu": "ちゅ",
            "cho": "ちょ",
            "nya": "にゃ",
            "nyu": "にゅ",
            "nyo": "にょ",
            "hya": "ひゃ",
            "hyu": "ひゅ",
            "hyo": "ひょ",
            "mya": "みゃ",
            "myu": "みゅ",
            "myo": "みょ",
            "rya": "りゃ",
            "ryu": "りゅ",
            "ryo": "りょ",
            "gya": "ぎゃ",
            "gyu": "ぎゅ",
            "gyo": "ぎょ",
            "ja": "じゃ",
            "ju": "じゅ",
            "jo": "じょ",
            "bya": "びゃ",
            "byu": "びゅ",
            "byo": "びょ",
            "pya": "ぴゃ",
            "pyu": "ぴゅ",
            "pyo": "ぴょ",
        }

        # Simple algorithm to convert text to Japanese-like sounds
        result = ""
        text = text.lower()
        i = 0

        while i < len(text):
            found = False

            # Try to match 3-character combinations first
            if i < len(text) - 2:
                three_chars = text[i : i + 3]
                if three_chars in romanization_map:
                    result += romanization_map[three_chars]
                    i += 3
                    found = True
                    continue

            # Try to match 2-character combinations next
            if i < len(text) - 1:
                two_chars = text[i : i + 2]
                if two_chars in romanization_map:
                    result += romanization_map[two_chars]
                    i += 2
                    found = True
                    continue

            # Try to match single characters
            if text[i] in romanization_map:
                result += romanization_map[text[i]]
                i += 1
                found = True
                continue

            # If no match, just add the character as is
            result += text[i]
            i += 1

        return result

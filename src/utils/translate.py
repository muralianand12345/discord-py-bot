"""
Utility class for translating text to different languages.

This module provides translation functionality using Groq LLM API
with proper error handling, caching and rate limiting.
"""

import os
import time
import asyncio
import aiohttp
import json
import logging
from typing import Dict, Optional, Any
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
    """A simple Least Recently Used (LRU) cache."""

    def __init__(self, capacity: int):
        self.capacity = max(1, capacity)
        self.cache = OrderedDict()

    def get(self, key: str) -> Optional[str]:
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: str) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)


class Translate:
    """Utility class for translating text to different languages."""

    # Class-level cache and cooldown tracking
    _translation_cache = LRUCache(TRANSLATION_CACHE_SIZE)
    _last_request_time = 0
    _lock = asyncio.Lock()
    _request_count = 0
    _request_reset_time = 0

    @staticmethod
    async def to_japanese(text: str) -> str:
        """
        Translate text to Japanese using Groq LLM or fallback.

        Args:
            text: The text to translate

        Returns:
            Translated Japanese text
        """
        # Skip empty text
        if not text:
            return text

        # Skip if already Japanese
        if Translate.is_japanese(text):
            logger.info(
                f"Skipping translation for '{text}' as it's already in Japanese"
            )
            return text

        # Truncate if too long
        if len(text) > MAX_TRANSLATION_LENGTH:
            text = text[:MAX_TRANSLATION_LENGTH]

        # Check cache first
        cached_result = Translate._translation_cache.get(f"ja:{text}")
        if cached_result:
            return cached_result

        # Enforce cooldown between requests
        async with Translate._lock:
            # Handle rate limiting
            current_time = time.time()

            # Reset counter if a minute has passed
            if current_time - Translate._request_reset_time >= 60:
                Translate._request_count = 0
                Translate._request_reset_time = current_time

            # Check if we're at the rate limit
            if Translate._request_count >= MAX_REQUESTS_PER_MINUTE:
                # If romanization fallback is enabled, use it instead of waiting
                if USE_ROMANIZATION_FALLBACK:
                    logger.warning("Rate limit reached, using romanization fallback")
                    result = await Translate._romanize_to_japanese(text)
                    Translate._translation_cache.put(f"ja:{text}", result)
                    return result

                # Otherwise wait until we can make a request
                wait_time = 60 - (current_time - Translate._request_reset_time)
                if wait_time > 0:
                    logger.warning(f"Rate limit reached. Waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    Translate._request_count = 0
                    Translate._request_reset_time = time.time()

            # Enforce cooldown between individual requests
            elapsed = current_time - Translate._last_request_time
            if elapsed < TRANSLATION_COOLDOWN_SECONDS:
                await asyncio.sleep(TRANSLATION_COOLDOWN_SECONDS - elapsed)

            # Update last request time
            Translate._last_request_time = time.time()
            Translate._request_count += 1

        try:
            # If no API key is available, use romanization
            if not GROQ_API_KEY:
                result = await Translate._romanize_to_japanese(text)
            else:
                # Try to translate with Groq
                result = await Translate._translate_with_groq(text, "ja")

            # Cache the result
            Translate._translation_cache.put(f"ja:{text}", result)
            return result

        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            # Fall back to romanization
            if USE_ROMANIZATION_FALLBACK:
                result = await Translate._romanize_to_japanese(text)
                Translate._translation_cache.put(f"ja:{text}", result)
                return result
            return text

    @staticmethod
    def is_japanese(text: str) -> bool:
        """
        Check if a string contains Japanese characters.

        Args:
            text: The text to check

        Returns:
            True if the text contains Japanese characters, False otherwise
        """
        # Unicode ranges for Japanese characters
        # Hiragana (3040-309F), Katakana (30A0-30FF), Kanji (4E00-9FFF)
        for char in text:
            if any(
                [
                    "\u3040" <= char <= "\u309f",  # Hiragana
                    "\u30a0" <= char <= "\u30ff",  # Katakana
                    "\u4e00" <= char <= "\u9fff",  # Kanji
                ]
            ):
                return True
        return False

    @staticmethod
    async def _translate_with_groq(text: str, target_language: str) -> str:
        """
        Translate text using the Groq LLM API.

        Args:
            text: The text to translate
            target_language: Target language code

        Returns:
            Translated text
        """
        # Simple validation
        if not text or not target_language:
            return text

        if not GROQ_API_KEY:
            raise ValueError("No Groq API key available")

        try:
            endpoint = f"{GROQ_API_BASE}/chat/completions"

            # Prepare messages for the LLM
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are a translator that specializes in converting names to {target_language}. "
                        "Respond with ONLY the translated name."
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
                "temperature": 0.2,
                "max_tokens": 150,
            }

            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint, json=payload, headers=headers, timeout=10
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Groq API error: {error_text}")
                        raise Exception(f"API error: {response.status}")

                    data = await response.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    return content

        except Exception as e:
            logger.error(f"Translation request failed: {str(e)}")
            raise

    @staticmethod
    async def translate_text(text: str, target_language: str) -> str:
        """
        Translate text to a specified language.

        Args:
            text: The text to translate
            target_language: Target language code

        Returns:
            Translated text
        """
        # For Japanese, use the specialized method
        if target_language.lower() == "ja":
            return await Translate.to_japanese(text)

        # For other languages, use the general method
        # Check cache first
        cached_result = Translate._translation_cache.get(f"{target_language}:{text}")
        if cached_result:
            return cached_result

        try:
            result = await Translate._translate_with_groq(text, target_language)
            Translate._translation_cache.put(f"{target_language}:{text}", result)
            return result
        except Exception:
            return text

    @staticmethod
    async def _romanize_to_japanese(text: str) -> str:
        """
        Simple fallback method to create a Japanese-like version of text.

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
            # Additional mappings for more complete coverage
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
        }

        # Simple algorithm to convert text to Japanese-like sounds
        result = ""
        text = text.lower()
        i = 0

        while i < len(text):
            found = False

            # Try to match 2-character combinations first
            if i < len(text) - 1:
                two_chars = text[i : i + 2]
                if two_chars in romanization_map:
                    result += romanization_map[two_chars]
                    i += 2
                    found = True
                    continue

            # If no 2-character match, try 1-character
            if text[i] in romanization_map:
                result += romanization_map[text[i]]
                i += 1
                found = True
                continue

            # If no match, just add the character as is
            result += text[i]
            i += 1

        return result

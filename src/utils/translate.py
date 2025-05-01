"""
Utility class for translating text to different languages.

This module provides translation functionality using the OpenAI-compatible LLM API
with proper error handling, caching and rate limiting.
"""

import logging
from collections import OrderedDict
from typing import Optional

from utils.llm import LLM
from utils.settings import (
    MAX_TRANSLATION_LENGTH,
    PROMPTS,
    TRANSLATION_CACHE_SIZE,
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

    # Class-level cache and LLM instance
    _translation_cache = LRUCache(TRANSLATION_CACHE_SIZE)
    _llm = None

    @classmethod
    def _get_llm(cls):
        """Get or create the LLM instance."""
        if cls._llm is None:
            cls._llm = LLM()
        return cls._llm

    @staticmethod
    async def to_japanese(text: str) -> str:
        """
        Translate text to Japanese using LLM or fallback.

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

        try:
            # Use the LLM to translate
            result = await Translate._translate_with_llm(text, "ja")

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
    async def _translate_with_llm(text: str, target_language: str) -> str:
        """
        Translate text using the LLM API.

        Args:
            text: The text to translate
            target_language: Target language code

        Returns:
            Translated text
        """
        # Simple validation
        if not text or not target_language:
            return text

        try:
            # Get the LLM instance
            llm = Translate._get_llm()

            # Get prompts from settings
            system_message = PROMPTS["translation"]["system_message"].format(
                language=target_language
            )
            user_message = PROMPTS["translation"]["user_message"].format(
                language=target_language, text=text
            )

            # Prepare messages for the LLM
            messages = [
                {
                    "role": "system",
                    "content": system_message,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ]

            # Call the LLM - removed temperature parameter as it's not supported by Groq
            content = await llm.invoke(messages)
            return content if content else text

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
            result = await Translate._translate_with_llm(text, target_language)
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

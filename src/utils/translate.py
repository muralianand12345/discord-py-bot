import aiohttp
import json
import os
from typing import Optional, Dict, Any


class Translate:
    """Utility class for translating text to different languages."""

    @staticmethod
    async def to_japanese(text: str) -> str:
        """
        Translate text to Japanese using an external translation API.

        Args:
            text: The text to translate

        Returns:
            Translated Japanese text
        """
        # Use environment variable or default to a free translation API
        api_key = os.getenv("TRANSLATE_API_KEY")
        api_url = os.getenv(
            "TRANSLATE_API_URL",
            "https://translation.googleapis.com/language/translate/v2",
        )

        # If no API key is available, use a simple romanization
        if not api_key:
            return await Translate._romanize_to_japanese(text)

        async with aiohttp.ClientSession() as session:
            try:
                payload = {"q": text, "target": "ja", "format": "text", "key": api_key}

                async with session.post(api_url, data=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        translated = (
                            data.get("data", {})
                            .get("translations", [{}])[0]
                            .get("translatedText", text)
                        )
                        return translated
                    else:
                        # Fall back to romanization on API failure
                        return await Translate._romanize_to_japanese(text)
            except Exception:
                # Fall back to romanization on exception
                return await Translate._romanize_to_japanese(text)

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

            # If no 2-character match, try 1-character
            if not found and text[i] in romanization_map:
                result += romanization_map[text[i]]
                i += 1
                found = True

            # If no match, just add the character as is
            if not found:
                result += text[i]
                i += 1

        return result

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
        api_key = os.getenv("TRANSLATE_API_KEY")
        api_url = os.getenv(
            "TRANSLATE_API_URL",
            "https://translation.googleapis.com/language/translate/v2",
        )

        # If no API key, return original text
        if not api_key:
            return text

        async with aiohttp.ClientSession() as session:
            try:
                payload = {
                    "q": text,
                    "target": target_language,
                    "format": "text",
                    "key": api_key,
                }

                async with session.post(api_url, data=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        translated = (
                            data.get("data", {})
                            .get("translations", [{}])[0]
                            .get("translatedText", text)
                        )
                        return translated
                    else:
                        return text
            except Exception:
                return text

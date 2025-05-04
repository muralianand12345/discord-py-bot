from config import LLM
from bot import logger
from utils.llm import LLMClient, LLMMessage
from utils.persistent_settings import PersistentSettings


class Translator:
    """
    Utility class for translating text using LLM services.
    This class handles translation services across the application.
    """

    # Default settings key
    SETTINGS_KEY = "translation_language"

    @staticmethod
    async def translate_name(name: str, language: str = None) -> str:
        """
        Translates a name to the specified language using LLM.

        Args:
            name: The name to translate
            language: Target language for translation (optional, uses persistent setting if None)

        Returns:
            Translated name or original if translation fails
        """
        # If no language specified, get from settings
        if language is None:
            language = await Translator.get_translation_language()

        # Skip translation if name is already in non-latin characters
        if any(ord(char) > 127 for char in name):
            return name

        if LLM.TRANSLATOR.API_KEY:
            try:
                # Create LLM client
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
                    content=f"""Translate the name "{name}" to {language}.
                    If the name has a common {language} equivalent, use that.
                    Otherwise, use phonetic representation that sounds similar in {language}.
                    Just provide the translated name without explanation.
                    """,
                )

                # Simple invocation with no fallback
                response = await llm_client.invoke(
                    messages=[prompt],
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

                    # If we have a valid response, return it
                    if response.strip():
                        return response

            except Exception as e:
                logger.error(f"Failed to translate name using LLM: {str(e)}")

        # Return original name if translation fails
        return name

    @staticmethod
    async def set_translation_language(language: str) -> None:
        """
        Sets the persistent translation language.

        Args:
            language: The language to set as default
        """
        settings = PersistentSettings()
        settings.set(Translator.SETTINGS_KEY, language)
        logger.info(f"Default translation language set to: {language}")

    @staticmethod
    async def get_translation_language() -> str:
        """
        Gets the configured translation language from persistent settings,
        falling back to config if not found.

        Returns:
            The configured language for translation
        """
        settings = PersistentSettings()
        # Get from persistent settings or fall back to config
        language = settings.get(Translator.SETTINGS_KEY)

        if not language:
            # Use the default from config
            language = getattr(LLM.TRANSLATOR, "LANGUAGE", "Arabic")
            # Store it for future use
            await Translator.set_translation_language(language)

        return language

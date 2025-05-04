import json
import os
from typing import Any, Dict


class PersistentSettings:
    """
    Utility class for storing and retrieving persistent settings across bot restarts.
    """

    _instance = None
    _settings: Dict[str, Any] = {}
    _settings_file = "data/settings.json"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PersistentSettings, cls).__new__(cls)
            cls._load_settings()
        return cls._instance

    @classmethod
    def _load_settings(cls) -> None:
        """Load settings from the JSON file."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(cls._settings_file), exist_ok=True)

        # Try to load existing settings
        if os.path.exists(cls._settings_file):
            try:
                with open(cls._settings_file, "r", encoding="utf-8") as f:
                    cls._settings = json.load(f)
            except Exception as e:
                print(f"Error loading settings: {str(e)}")
                cls._settings = {}
        else:
            cls._settings = {}

    @classmethod
    def _save_settings(cls) -> None:
        """Save settings to the JSON file."""
        try:
            with open(cls._settings_file, "w", encoding="utf-8") as f:
                json.dump(cls._settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving settings: {str(e)}")

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        Retrieve a setting value by key.

        Args:
            key: The setting key
            default: Default value if key is not found

        Returns:
            The setting value or default
        """
        cls._load_settings()  # Ensure we have the latest settings
        return cls._settings.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """
        Store a setting value.

        Args:
            key: The setting key
            value: The value to store
        """
        cls._settings[key] = value
        cls._save_settings()

    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """
        Get all settings.

        Returns:
            Dictionary containing all settings
        """
        cls._load_settings()  # Ensure we have the latest settings
        return cls._settings.copy()

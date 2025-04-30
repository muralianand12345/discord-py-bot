"""
Database manager for Discord bot storage.
Supports both SQLite and JSON file storage.
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional, Union
import threading

from utils.settings import DB_TYPE, DB_PATH


class DatabaseManager:
    """Database manager for Discord bot storage."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Implement singleton pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize database manager."""
        if self._initialized:
            return

        self.logger = logging.getLogger("db_manager")
        self.db_type = DB_TYPE.lower()
        self.db_path = DB_PATH

        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Initialize the appropriate database
        if self.db_type == "sqlite":
            self._init_sqlite()
        elif self.db_type == "json":
            self._init_json()
        else:
            self.logger.error(
                f"Unsupported database type: {self.db_type}. Falling back to SQLite."
            )
            self.db_type = "sqlite"
            self._init_sqlite()

        self._initialized = True
        self.logger.info(f"Database initialized: {self.db_type}")

    def _init_sqlite(self):
        """Initialize SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            self.cursor = self.conn.cursor()

            # Create tables if they don't exist
            self._create_tables()

        except sqlite3.Error as e:
            self.logger.error(f"SQLite initialization error: {str(e)}")
            raise

    def _init_json(self):
        """Initialize JSON file storage."""
        self.data = {}

        # Load existing data if file exists
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except json.JSONDecodeError:
                self.logger.error("Invalid JSON file. Creating new database.")
                self.data = {}
            except Exception as e:
                self.logger.error(f"Failed to load JSON database: {str(e)}")
                self.data = {}

    def _create_tables(self):
        """Create required tables for SQLite database."""
        # Create settings table
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS settings (
            guild_id INTEGER PRIMARY KEY,
            settings_json TEXT NOT NULL
        )
        """
        )

        # Create user data table
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS user_data (
            user_id INTEGER PRIMARY KEY,
            data_json TEXT NOT NULL
        )
        """
        )

        # Create translations cache table
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS translations (
            original TEXT NOT NULL,
            language TEXT NOT NULL,
            translation TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            PRIMARY KEY (original, language)
        )
        """
        )

        self.conn.commit()

    def _save_json(self):
        """Save JSON data to file."""
        if self.db_type != "json":
            return

        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save JSON database: {str(e)}")

    def get_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        """
        Get settings for a specific guild.

        Args:
            guild_id: Discord guild ID

        Returns:
            Dictionary containing guild settings
        """
        if self.db_type == "sqlite":
            self.cursor.execute(
                "SELECT settings_json FROM settings WHERE guild_id = ?", (guild_id,)
            )
            row = self.cursor.fetchone()

            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON in settings for guild {guild_id}")
                    return {}
            else:
                return {}

        elif self.db_type == "json":
            return self.data.get("guild_settings", {}).get(str(guild_id), {})

    def save_guild_settings(self, guild_id: int, settings: Dict[str, Any]) -> bool:
        """
        Save settings for a specific guild.

        Args:
            guild_id: Discord guild ID
            settings: Dictionary containing guild settings

        Returns:
            Success status
        """
        try:
            if self.db_type == "sqlite":
                settings_json = json.dumps(settings, ensure_ascii=False)

                self.cursor.execute(
                    "INSERT OR REPLACE INTO settings (guild_id, settings_json) VALUES (?, ?)",
                    (guild_id, settings_json),
                )
                self.conn.commit()

            elif self.db_type == "json":
                if "guild_settings" not in self.data:
                    self.data["guild_settings"] = {}

                self.data["guild_settings"][str(guild_id)] = settings
                self._save_json()

            return True

        except Exception as e:
            self.logger.error(f"Failed to save guild settings: {str(e)}")
            return False

    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """
        Get data for a specific user.

        Args:
            user_id: Discord user ID

        Returns:
            Dictionary containing user data
        """
        if self.db_type == "sqlite":
            self.cursor.execute(
                "SELECT data_json FROM user_data WHERE user_id = ?", (user_id,)
            )
            row = self.cursor.fetchone()

            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON in data for user {user_id}")
                    return {}
            else:
                return {}

        elif self.db_type == "json":
            return self.data.get("user_data", {}).get(str(user_id), {})

    def save_user_data(self, user_id: int, data: Dict[str, Any]) -> bool:
        """
        Save data for a specific user.

        Args:
            user_id: Discord user ID
            data: Dictionary containing user data

        Returns:
            Success status
        """
        try:
            if self.db_type == "sqlite":
                data_json = json.dumps(data, ensure_ascii=False)

                self.cursor.execute(
                    "INSERT OR REPLACE INTO user_data (user_id, data_json) VALUES (?, ?)",
                    (user_id, data_json),
                )
                self.conn.commit()

            elif self.db_type == "json":
                if "user_data" not in self.data:
                    self.data["user_data"] = {}

                self.data["user_data"][str(user_id)] = data
                self._save_json()

            return True

        except Exception as e:
            self.logger.error(f"Failed to save user data: {str(e)}")
            return False

    def save_translation(self, original: str, language: str, translation: str) -> bool:
        """
        Save a translation to the database.

        Args:
            original: Original text
            language: Target language code
            translation: Translated text

        Returns:
            Success status
        """
        import time

        timestamp = int(time.time())

        try:
            if self.db_type == "sqlite":
                self.cursor.execute(
                    "INSERT OR REPLACE INTO translations (original, language, translation, timestamp) VALUES (?, ?, ?, ?)",
                    (original, language, translation, timestamp),
                )
                self.conn.commit()

            elif self.db_type == "json":
                if "translations" not in self.data:
                    self.data["translations"] = {}

                key = f"{original}:{language}"
                self.data["translations"][key] = {
                    "translation": translation,
                    "timestamp": timestamp,
                }
                self._save_json()

            return True

        except Exception as e:
            self.logger.error(f"Failed to save translation: {str(e)}")
            return False

    def get_translation(self, original: str, language: str) -> Optional[str]:
        """
        Get a saved translation from the database.

        Args:
            original: Original text
            language: Target language code

        Returns:
            Translated text or None if not found
        """
        if self.db_type == "sqlite":
            self.cursor.execute(
                "SELECT translation FROM translations WHERE original = ? AND language = ?",
                (original, language),
            )
            row = self.cursor.fetchone()

            return row[0] if row else None

        elif self.db_type == "json":
            key = f"{original}:{language}"
            translation_data = self.data.get("translations", {}).get(key)

            return translation_data.get("translation") if translation_data else None

    def close(self):
        """Close database connection."""
        if self.db_type == "sqlite" and hasattr(self, "conn"):
            self.conn.close()
        elif self.db_type == "json":
            self._save_json()

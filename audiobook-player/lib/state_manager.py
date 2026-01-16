"""
State Manager Module for TaleTiles Audiobook Player

Handles persistent state including:
- RFID card to audiobook mappings
- Playback position per audiobook
- Global settings (volume)
- Audiobook registration
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import shutil

logger = logging.getLogger(__name__)

# Default config structure
DEFAULT_CONFIG = {
    "global_volume": 75,
    "audiobooks": {},
    "display": {
        "type": "eink",  # Options: "eink", "lcd1602"
        # LCD 1602 pin configuration (4-bit mode, BCM numbering)
        "lcd_rs": 16,
        "lcd_e": 18,
        "lcd_d4": 20,
        "lcd_d5": 21,
        "lcd_d6": 22,
        "lcd_d7": 23
    }
}


class AudiobookEntry:
    """Represents a registered audiobook with its state."""

    def __init__(self, card_id: str, data: dict):
        self.card_id = card_id
        self.path = data.get("path", "")
        self.title = data.get("title", "")
        self.current_file_index = data.get("current_file_index", 0)
        self.position_seconds = data.get("position_seconds", 0.0)
        self.last_played = data.get("last_played")
        self.added_date = data.get("added_date")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": self.path,
            "title": self.title,
            "current_file_index": self.current_file_index,
            "position_seconds": self.position_seconds,
            "last_played": self.last_played,
            "added_date": self.added_date,
        }

    def __repr__(self):
        return f"AudiobookEntry('{self.card_id}', '{self.title}')"


class StateManager:
    """
    Manages persistent state for the audiobook player.

    State is stored in config.json and includes:
    - Global volume setting
    - RFID card to audiobook folder mappings
    - Playback position per audiobook
    """

    def __init__(self, config_path: str | Path = "config.json"):
        """
        Initialize the state manager.

        Args:
            config_path: Path to the config.json file
        """
        self._config_path = Path(config_path)
        self._config: dict = {}
        self._dirty = False
        self._load()

    def _load(self):
        """Load config from disk."""
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                logger.info(f"Loaded config from {self._config_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load config: {e}")
                self._backup_and_reset()
        else:
            logger.info("No config file found, using defaults")
            self._config = DEFAULT_CONFIG.copy()
            self._config["audiobooks"] = {}
            self._dirty = True

    def _backup_and_reset(self):
        """Backup corrupted config and reset to defaults."""
        if self._config_path.exists():
            backup_path = self._config_path.with_suffix('.json.backup')
            shutil.copy(self._config_path, backup_path)
            logger.warning(f"Backed up corrupted config to {backup_path}")

        self._config = DEFAULT_CONFIG.copy()
        self._config["audiobooks"] = {}
        self._dirty = True

    def save(self):
        """Save config to disk."""
        if not self._dirty:
            return

        try:
            # Write to temp file first, then rename (atomic)
            temp_path = self._config_path.with_suffix('.json.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
            temp_path.rename(self._config_path)
            self._dirty = False
            logger.debug("Config saved")
        except IOError as e:
            logger.error(f"Failed to save config: {e}")

    def _mark_dirty(self):
        """Mark config as modified."""
        self._dirty = True

    # Global settings

    @property
    def volume(self) -> int:
        """Get global volume (0-100)."""
        return self._config.get("global_volume", 75)

    @volume.setter
    def volume(self, value: int):
        """Set global volume (0-100)."""
        value = max(0, min(100, value))
        if self._config.get("global_volume") != value:
            self._config["global_volume"] = value
            self._mark_dirty()

    @property
    def display_config(self) -> dict:
        """Get display configuration."""
        default_display = DEFAULT_CONFIG["display"]
        return self._config.get("display", default_display)

    # Audiobook management

    def get_audiobook(self, card_id: str) -> Optional[AudiobookEntry]:
        """
        Get audiobook entry for a card ID.

        Args:
            card_id: The RFID card ID

        Returns:
            AudiobookEntry if found, None otherwise
        """
        audiobooks = self._config.get("audiobooks", {})
        if card_id in audiobooks:
            return AudiobookEntry(card_id, audiobooks[card_id])
        return None

    def get_all_audiobooks(self) -> list[AudiobookEntry]:
        """Get all registered audiobooks."""
        audiobooks = self._config.get("audiobooks", {})
        return [AudiobookEntry(cid, data) for cid, data in audiobooks.items()]

    def register_audiobook(self, card_id: str, path: str | Path, title: str) -> AudiobookEntry:
        """
        Register a new audiobook with an RFID card.

        Args:
            card_id: The RFID card ID
            path: Path to the audiobook folder
            title: Display title for the audiobook

        Returns:
            The created AudiobookEntry
        """
        path = str(Path(path).resolve())

        entry_data = {
            "path": path,
            "title": title,
            "current_file_index": 0,
            "position_seconds": 0.0,
            "last_played": None,
            "added_date": datetime.now().isoformat(),
        }

        if "audiobooks" not in self._config:
            self._config["audiobooks"] = {}

        self._config["audiobooks"][card_id] = entry_data
        self._mark_dirty()
        self.save()

        logger.info(f"Registered audiobook: {title} (card: {card_id})")
        return AudiobookEntry(card_id, entry_data)

    def unregister_audiobook(self, card_id: str) -> bool:
        """
        Remove an audiobook registration.

        Args:
            card_id: The RFID card ID to unregister

        Returns:
            True if removed, False if not found
        """
        audiobooks = self._config.get("audiobooks", {})
        if card_id in audiobooks:
            del audiobooks[card_id]
            self._mark_dirty()
            self.save()
            logger.info(f"Unregistered card: {card_id}")
            return True
        return False

    def update_playback_position(self, card_id: str, file_index: int, position: float):
        """
        Update the saved playback position for an audiobook.

        Args:
            card_id: The RFID card ID
            file_index: Current file index in playlist
            position: Position in seconds within the file
        """
        audiobooks = self._config.get("audiobooks", {})
        if card_id in audiobooks:
            audiobooks[card_id]["current_file_index"] = file_index
            audiobooks[card_id]["position_seconds"] = position
            audiobooks[card_id]["last_played"] = datetime.now().isoformat()
            self._mark_dirty()

    def find_card_by_path(self, path: str | Path) -> Optional[str]:
        """
        Find the card ID registered to a given audiobook path.

        Args:
            path: Path to the audiobook folder

        Returns:
            Card ID if found, None otherwise
        """
        path = str(Path(path).resolve())
        audiobooks = self._config.get("audiobooks", {})
        for card_id, data in audiobooks.items():
            if data.get("path") == path:
                return card_id
        return None

    def validate_paths(self) -> list[tuple[str, str, str]]:
        """
        Check all registered audiobooks for missing paths.

        Returns:
            List of (card_id, title, path) for missing audiobooks
        """
        missing = []
        audiobooks = self._config.get("audiobooks", {})
        for card_id, data in audiobooks.items():
            path = Path(data.get("path", ""))
            if not path.exists():
                missing.append((card_id, data.get("title", "Unknown"), str(path)))
        return missing

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()
        return False

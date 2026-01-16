"""
Audio Player Module for TaleTiles Audiobook Player

Handles audiobook playback using mpv, including:
- Loading audiobooks from folders with metadata.json
- Chapter navigation across multiple audio files
- Position tracking and seeking
- Volume control
"""

import json
import logging
from pathlib import Path
from typing import Optional, Callable
import mpv

logger = logging.getLogger(__name__)


class Chapter:
    """Represents a chapter within an audiobook."""

    def __init__(self, index: int, title: str, spine: int, offset: float):
        self.index = index
        self.title = title
        self.spine = spine  # Index into the files list (Part 001 = 0, Part 002 = 1, etc.)
        self.offset = offset  # Seconds from start of that file

    def __repr__(self):
        return f"Chapter({self.index}, '{self.title}', spine={self.spine}, offset={self.offset})"


class AudioPlayer:
    """
    Audiobook player using mpv backend.

    Supports audiobooks with:
    - Multiple Part files (Part 001.mp3, Part 002.mp3, etc.)
    - metadata.json with chapter markers
    - Position tracking and resume
    """

    def __init__(self):
        self._player: Optional[mpv.MPV] = None
        self._audiobook_path: Optional[Path] = None
        self._metadata: Optional[dict] = None
        self._files: list[Path] = []
        self._spine_durations: list[float] = []
        self._chapters: list[Chapter] = []
        self._current_file_index: int = 0
        self._volume: int = 75
        self._on_file_end: Optional[Callable] = None
        self._is_playing: bool = False

    def _init_player(self):
        """Initialize or reinitialize the mpv player."""
        if self._player:
            self._player.terminate()

        self._player = mpv.MPV(
            video=False,
            terminal=False,
            input_default_bindings=False,
            input_vo_keyboard=False,
        )
        self._player.volume = self._volume

        @self._player.event_callback('end-file')
        def on_end_file(event):
            # MpvEvent object - check reason attribute
            reason = getattr(event, 'reason', None)
            if reason is None and hasattr(event, 'event'):
                reason = getattr(event.event, 'reason', None)
            if reason == 'eof' or str(reason) == 'eof':
                self._handle_file_end()

    def _handle_file_end(self):
        """Handle end of current file - advance to next if available."""
        if self._current_file_index < len(self._files) - 1:
            self._current_file_index += 1
            self._play_current_file(start_position=0)
        else:
            self._is_playing = False
            logger.info("Audiobook finished")
            if self._on_file_end:
                self._on_file_end()

    def _play_current_file(self, start_position: float = 0):
        """Start playing the current file from the given position."""
        if not self._files or self._current_file_index >= len(self._files):
            return

        file_path = self._files[self._current_file_index]
        logger.info(f"Playing file {self._current_file_index + 1}/{len(self._files)}: {file_path.name}")

        self._player.play(str(file_path))
        if start_position > 0:
            self._player.wait_until_playing()
            self._player.seek(start_position, reference='absolute')
        self._is_playing = True

    def load_audiobook(self, audiobook_path: str | Path) -> bool:
        """
        Load an audiobook from a folder.

        Expected folder structure:
        - Part 001.mp3, Part 002.mp3, etc. (or other audio files)
        - metadata/metadata.json (optional but recommended)

        Returns True if loaded successfully.
        """
        path = Path(audiobook_path)
        if not path.is_dir():
            logger.error(f"Audiobook path is not a directory: {path}")
            return False

        # Find audio files (sorted alphabetically)
        audio_extensions = {'.mp3', '.m4a', '.m4b', '.ogg', '.flac', '.wav'}
        self._files = sorted([
            f for f in path.iterdir()
            if f.is_file() and f.suffix.lower() in audio_extensions and not f.name.startswith('.')
        ])

        if not self._files:
            logger.error(f"No audio files found in: {path}")
            return False

        logger.info(f"Found {len(self._files)} audio files")

        # Load metadata if available
        metadata_path = path / "metadata" / "metadata.json"
        if metadata_path.exists():
            self._load_metadata(metadata_path)
        else:
            logger.warning("No metadata.json found, chapter navigation will be limited")
            self._metadata = None
            self._chapters = []
            self._spine_durations = []

        self._audiobook_path = path
        self._current_file_index = 0
        self._init_player()

        return True

    def _load_metadata(self, metadata_path: Path):
        """Load and parse metadata.json."""
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self._metadata = json.load(f)

            # Extract spine durations
            self._spine_durations = [
                item.get('duration', 0) for item in self._metadata.get('spine', [])
            ]

            # Build chapter list
            self._chapters = []
            for i, ch in enumerate(self._metadata.get('chapters', [])):
                self._chapters.append(Chapter(
                    index=i,
                    title=ch.get('title', f'Chapter {i + 1}'),
                    spine=ch.get('spine', 0),
                    offset=ch.get('offset', 0)
                ))

            logger.info(f"Loaded metadata: {len(self._chapters)} chapters")

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load metadata: {e}")
            self._metadata = None
            self._chapters = []
            self._spine_durations = []

    @property
    def title(self) -> str:
        """Get the audiobook title."""
        if self._metadata:
            return self._metadata.get('title', '')
        if self._audiobook_path:
            return self._audiobook_path.name
        return ''

    @property
    def is_loaded(self) -> bool:
        """Check if an audiobook is loaded."""
        return bool(self._files)

    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._is_playing and self._player and not self._player.pause

    @property
    def volume(self) -> int:
        """Get current volume (0-100)."""
        return self._volume

    @volume.setter
    def volume(self, value: int):
        """Set volume (0-100)."""
        self._volume = max(0, min(100, value))
        if self._player:
            self._player.volume = self._volume

    @property
    def position(self) -> float:
        """Get current position in seconds within the current file."""
        if self._player and self._player.time_pos is not None:
            return self._player.time_pos
        return 0.0

    @property
    def total_position(self) -> float:
        """Get current position in seconds from the start of the audiobook."""
        pos = self.position
        for i in range(self._current_file_index):
            if i < len(self._spine_durations):
                pos += self._spine_durations[i]
        return pos

    @property
    def duration(self) -> float:
        """Get duration of current file in seconds."""
        if self._player and self._player.duration is not None:
            return self._player.duration
        return 0.0

    @property
    def total_duration(self) -> float:
        """Get total duration of the audiobook in seconds."""
        return sum(self._spine_durations) if self._spine_durations else self.duration

    @property
    def current_file_index(self) -> int:
        """Get the index of the currently playing file."""
        return self._current_file_index

    @property
    def file_count(self) -> int:
        """Get the total number of audio files."""
        return len(self._files)

    @property
    def chapters(self) -> list[Chapter]:
        """Get the list of chapters."""
        return self._chapters.copy()

    @property
    def current_chapter(self) -> Optional[Chapter]:
        """Get the current chapter based on playback position."""
        if not self._chapters:
            return None

        current_spine = self._current_file_index
        current_pos = self.position

        # Find the last chapter that starts before or at current position
        current = None
        for ch in self._chapters:
            if ch.spine < current_spine:
                current = ch
            elif ch.spine == current_spine and ch.offset <= current_pos:
                current = ch
            elif ch.spine > current_spine:
                break

        return current

    @property
    def chapter_count(self) -> int:
        """Get the total number of chapters."""
        return len(self._chapters)

    def play(self):
        """Start or resume playback."""
        if not self._files:
            logger.warning("No audiobook loaded")
            return

        if self._player:
            if self._player.pause:
                self._player.pause = False
                self._is_playing = True
            elif not self._is_playing:
                self._play_current_file()

    def pause(self):
        """Pause playback."""
        if self._player and not self._player.pause:
            self._player.pause = True
            self._is_playing = False

    def toggle_playback(self):
        """Toggle between play and pause."""
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def seek(self, seconds: float, relative: bool = True):
        """
        Seek within the audiobook.

        Args:
            seconds: Number of seconds to seek (positive or negative)
            relative: If True, seek relative to current position; if False, absolute
        """
        if not self._player:
            return

        if relative:
            self._player.seek(seconds, reference='relative')
        else:
            self._player.seek(seconds, reference='absolute')

    def seek_to_position(self, file_index: int, position: float):
        """
        Seek to a specific position in a specific file.

        Args:
            file_index: Index of the file (0-based)
            position: Position in seconds within that file
        """
        if not self._files or file_index >= len(self._files):
            return

        if file_index != self._current_file_index:
            self._current_file_index = file_index
            self._play_current_file(start_position=position)
        else:
            self.seek(position, relative=False)

    def next_chapter(self):
        """Skip to the next chapter."""
        if not self._chapters:
            # No chapters - skip to next file
            if self._current_file_index < len(self._files) - 1:
                self._current_file_index += 1
                self._play_current_file()
            return

        current = self.current_chapter
        if current is None:
            return

        next_idx = current.index + 1
        if next_idx < len(self._chapters):
            ch = self._chapters[next_idx]
            self.seek_to_position(ch.spine, ch.offset)
            logger.info(f"Skipped to chapter: {ch.title}")

    def previous_chapter(self):
        """
        Skip to the previous chapter.
        If more than 5 seconds into current chapter, restart it instead.
        """
        if not self._chapters:
            # No chapters - skip to previous file or restart current
            if self.position > 5:
                self.seek(0, relative=False)
            elif self._current_file_index > 0:
                self._current_file_index -= 1
                self._play_current_file()
            return

        current = self.current_chapter
        if current is None:
            return

        # If more than 5 seconds into chapter, restart it
        chapter_position = self.position - current.offset if current.spine == self._current_file_index else self.position
        if chapter_position > 5:
            self.seek_to_position(current.spine, current.offset)
            logger.info(f"Restarted chapter: {current.title}")
            return

        # Otherwise go to previous chapter
        prev_idx = current.index - 1
        if prev_idx >= 0:
            ch = self._chapters[prev_idx]
            self.seek_to_position(ch.spine, ch.offset)
            logger.info(f"Skipped to chapter: {ch.title}")

    def get_state(self) -> dict:
        """
        Get the current playback state for persistence.

        Returns dict with:
        - file_index: Current file index
        - position: Position in current file (seconds)
        - volume: Current volume
        """
        return {
            'file_index': self._current_file_index,
            'position': self.position,
            'volume': self._volume,
        }

    def restore_state(self, state: dict):
        """
        Restore playback state from a saved state dict.

        Args:
            state: Dict with file_index, position, and optionally volume
        """
        file_index = state.get('file_index', 0)
        position = state.get('position', 0)
        volume = state.get('volume')

        if volume is not None:
            self.volume = volume

        if file_index < len(self._files):
            self._current_file_index = file_index

        # Store position to seek to after play() is called
        self._restore_position = position

    def play_from_state(self):
        """Start playback from restored state."""
        position = getattr(self, '_restore_position', 0)
        self._play_current_file(start_position=position)
        self._restore_position = 0

    def stop(self):
        """Stop playback and release resources."""
        if self._player:
            self._player.stop()
            self._is_playing = False

    def cleanup(self):
        """Clean up resources."""
        if self._player:
            self._player.terminate()
            self._player = None
        self._is_playing = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False

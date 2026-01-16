#!/usr/bin/env python3
"""
TaleTiles Audiobook Player - Main Application

RFID-controlled audiobook player for children.
Place a card to play, remove to pause and save position.

Usage:
    python player.py [--mock] [--audiobooks PATH]

Options:
    --mock              Use mock RFID mode (for testing without hardware)
    --audiobooks PATH   Path to audiobooks folder (default: ../AudioBooks)
"""

import argparse
import logging
import signal
import sys
import threading
import time
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.audio_player import AudioPlayer
from lib.rfid_handler import RFIDHandler
from lib.state_manager import StateManager
from lib.button_handler import ButtonHandler, Button, KEYBOARD_MAP
from lib.display_manager import DisplayManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s]: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('player')

# Position save interval (seconds)
POSITION_SAVE_INTERVAL = 30


class TaleTilesPlayer:
    """
    Main audiobook player application.

    Coordinates RFID detection, audio playback, and state persistence.
    """

    def __init__(self, config_path: Path, audiobooks_path: Path, mock_mode: bool = False):
        self.audiobooks_path = audiobooks_path
        self.mock_mode = mock_mode

        # Initialize components
        self.state = StateManager(config_path)
        self.audio = AudioPlayer()
        self.rfid = RFIDHandler(mock_mode=mock_mode)
        self.buttons = ButtonHandler(mock_mode=mock_mode)

        # Initialize display with config
        display_config = self.state.display_config
        self.display = DisplayManager(
            mock_mode=mock_mode,
            display_type=display_config.get("type", "eink"),
            lcd_config=display_config
        )

        # Current state
        self._current_card_id: str | None = None
        self._running = False
        self._position_save_thread: threading.Thread | None = None
        self._keyboard_thread: threading.Thread | None = None

        # Register RFID callbacks
        self.rfid.on_card_placed(self._on_card_placed)
        self.rfid.on_card_removed(self._on_card_removed)

        # Register button callbacks
        self.buttons.on_play_pause(self.toggle_playback)
        self.buttons.on_volume_up(self.volume_up)
        self.buttons.on_volume_down(self.volume_down)
        self.buttons.on_skip_back(self.skip_back)
        self.buttons.on_skip_back_double(self.previous_chapter)
        self.buttons.on_skip_forward(self.skip_forward)
        self.buttons.on_skip_forward_double(self.next_chapter)

    def _on_card_placed(self, card_id: str):
        """Handle RFID card placement."""
        logger.info(f"Card placed: {card_id}")
        self._current_card_id = card_id

        # Look up the audiobook for this card
        entry = self.state.get_audiobook(card_id)

        if entry is None:
            logger.warning(f"Unknown card: {card_id}")
            self.display.show_unknown_card(card_id)
            return

        # Check if audiobook path exists
        if not Path(entry.path).exists():
            logger.error(f"Audiobook not found: {entry.path}")
            self.display.show_error(f"Missing: {entry.title}")
            return

        # Load and play the audiobook
        logger.info(f"Loading audiobook: {entry.title}")
        self.display.show_loading(entry.title)

        if not self.audio.load_audiobook(entry.path):
            logger.error(f"Failed to load audiobook: {entry.path}")
            self.display.show_error("Load failed")
            return

        # Restore saved position
        self.audio.volume = self.state.volume
        if entry.current_file_index > 0 or entry.position_seconds > 0:
            logger.info(f"Resuming from file {entry.current_file_index}, position {entry.position_seconds:.1f}s")
            self.audio.restore_state({
                'file_index': entry.current_file_index,
                'position': entry.position_seconds,
            })
            self.audio.play_from_state()
        else:
            self.audio.play()

        self._update_display()

    def _on_card_removed(self, card_id: str):
        """Handle RFID card removal."""
        logger.info(f"Card removed: {card_id}")

        # Save position before stopping
        if self.audio.is_loaded:
            self._save_position(card_id)
            self.audio.stop()

        self._current_card_id = None
        self.display.show_ready()

    def _save_position(self, card_id: str | None = None):
        """Save current playback position."""
        if card_id is None:
            card_id = self._current_card_id

        if card_id is None or not self.audio.is_loaded:
            return

        file_index = self.audio.current_file_index
        position = self.audio.position

        self.state.update_playback_position(card_id, file_index, position)
        self.state.volume = self.audio.volume
        self.state.save()

        logger.debug(f"Saved position: file {file_index}, {position:.1f}s")

    def _position_save_loop(self):
        """Background loop to periodically save position."""
        while self._running:
            time.sleep(POSITION_SAVE_INTERVAL)
            if self._running and self.audio.is_playing:
                self._save_position()

    def _update_display(self):
        """Update the display with current playback state."""
        if not self.audio.is_loaded:
            self.display.show_ready()
            return

        chapter = self.audio.current_chapter
        chapter_num = chapter.index + 1 if chapter else 0
        chapter_title = chapter.title if chapter else ""

        # Calculate time remaining
        time_remaining = self.audio.total_duration - self.audio.total_position

        if self.audio.is_playing:
            self.display.show_playing(
                title=self.audio.title,
                chapter_num=chapter_num,
                chapter_total=self.audio.chapter_count,
                chapter_title=chapter_title,
                time_remaining=time_remaining,
                volume=self.audio.volume
            )
        else:
            self.display.show_paused(
                title=self.audio.title,
                chapter_num=chapter_num,
                chapter_total=self.audio.chapter_count,
                chapter_title=chapter_title,
                time_remaining=time_remaining,
                volume=self.audio.volume
            )

    def start(self):
        """Start the player."""
        logger.info("Starting TaleTiles player...")

        self._running = True

        # Start RFID monitoring
        self.rfid.start()

        # Start button handler
        self.buttons.start()

        # Start display manager
        self.display.start()

        # Start position save thread
        self._position_save_thread = threading.Thread(
            target=self._position_save_loop,
            daemon=True
        )
        self._position_save_thread.start()

        # Start keyboard input thread for mock mode
        if self.mock_mode:
            self._keyboard_thread = threading.Thread(
                target=self._keyboard_input_loop,
                daemon=True
            )
            self._keyboard_thread.start()

        self.display.show_ready()
        self._show_controls()
        logger.info("Player started")

    def _keyboard_input_loop(self):
        """Handle keyboard input in mock mode."""
        import sys
        import tty
        import termios

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setcbreak(fd)
            while self._running:
                # Check if input is available
                import select
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    char = sys.stdin.read(1)

                    # Handle RFID card simulation
                    if char in '12345':
                        card_id = f"card{char}"
                        if self.rfid.current_card_id == card_id:
                            self.rfid.mock_remove_card()
                        else:
                            self.rfid.mock_place_card(card_id)
                    elif char == 'r':
                        self.rfid.mock_remove_card()
                    # Handle button simulation
                    elif char in KEYBOARD_MAP:
                        self.buttons.simulate_press(KEYBOARD_MAP[char])
                    elif char == 'i':
                        self._update_display()
                    elif char == 'h':
                        self._show_controls()

        except Exception as e:
            logger.debug(f"Keyboard input error: {e}")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _show_controls(self):
        """Show available controls in mock mode."""
        if self.mock_mode:
            print("\nControls:")
            print("  1-5     Simulate RFID card 1-5")
            print("  r       Remove current card")
            print("  Space   Play/Pause")
            print("  +/-     Volume Up/Down")
            print("  ,/.     Skip Back/Forward 30s")
            print("  </>     Previous/Next Chapter (double-tap ,/.)")
            print("  i       Show info")
            print("  h       Show this help")
            print("  Ctrl+C  Quit\n")

    def stop(self):
        """Stop the player and save state."""
        logger.info("Stopping player...")

        self._running = False

        # Save position if playing
        if self.audio.is_playing:
            self._save_position()

        # Stop components
        self.audio.cleanup()
        self.rfid.cleanup()
        self.buttons.cleanup()
        self.display.cleanup()
        self.state.save()

        logger.info("Player stopped")

    def run(self):
        """Run the player main loop."""
        self.start()

        try:
            while self._running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Interrupted")
        finally:
            self.stop()

    # Playback controls (for button integration in Phase 4)

    def toggle_playback(self):
        """Toggle play/pause."""
        if self.audio.is_loaded:
            self.audio.toggle_playback()
            status = "Playing" if self.audio.is_playing else "Paused"
            logger.info(status)
            self._update_display()

    def volume_up(self, amount: int = 5):
        """Increase volume."""
        if self.audio.is_loaded:
            self.audio.volume = self.audio.volume + amount
            self.state.volume = self.audio.volume
            logger.info(f"Volume: {self.audio.volume}%")
            self._update_display()

    def volume_down(self, amount: int = 5):
        """Decrease volume."""
        if self.audio.is_loaded:
            self.audio.volume = self.audio.volume - amount
            self.state.volume = self.audio.volume
            logger.info(f"Volume: {self.audio.volume}%")
            self._update_display()

    def skip_forward(self, seconds: float = 30):
        """Skip forward."""
        if self.audio.is_loaded:
            self.audio.seek(seconds)
            logger.info(f"Skipped forward {seconds}s")
            self._update_display()

    def skip_back(self, seconds: float = 30):
        """Skip backward."""
        if self.audio.is_loaded:
            self.audio.seek(-seconds)
            logger.info(f"Skipped back {seconds}s")
            self._update_display()

    def next_chapter(self):
        """Skip to next chapter."""
        if self.audio.is_loaded:
            self.audio.next_chapter()
            if self.audio.current_chapter:
                logger.info(f"Chapter: {self.audio.current_chapter.title}")
            self._update_display()

    def previous_chapter(self):
        """Skip to previous chapter."""
        if self.audio.is_loaded:
            self.audio.previous_chapter()
            if self.audio.current_chapter:
                logger.info(f"Chapter: {self.audio.current_chapter.title}")
            self._update_display()


def main():
    parser = argparse.ArgumentParser(description='TaleTiles Audiobook Player')
    parser.add_argument('--mock', action='store_true',
                        help='Use mock RFID mode for testing')
    parser.add_argument('--audiobooks', type=str, default='../AudioBooks',
                        help='Path to audiobooks folder')
    parser.add_argument('--config', type=str, default='config.json',
                        help='Path to config file')
    args = parser.parse_args()

    # Resolve paths
    base_path = Path(__file__).parent
    config_path = base_path / args.config
    audiobooks_path = Path(args.audiobooks)
    if not audiobooks_path.is_absolute():
        audiobooks_path = base_path / audiobooks_path

    logger.info(f"Config: {config_path}")
    logger.info(f"Audiobooks: {audiobooks_path}")
    logger.info(f"Mock mode: {args.mock}")

    # Create and run player
    player = TaleTilesPlayer(
        config_path=config_path,
        audiobooks_path=audiobooks_path,
        mock_mode=args.mock
    )

    # Handle signals gracefully
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        player.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    player.run()


if __name__ == '__main__':
    main()

"""
RFID Handler Module for TaleTiles Audiobook Player

Handles RFID card detection using the RC522 module:
- Continuous card presence monitoring
- Card placement and removal events
- Debouncing for reliable detection
- Mock mode for development without hardware
"""

import logging
import threading
import time
from typing import Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class CardEvent(Enum):
    """Types of card events."""
    PLACED = "placed"
    REMOVED = "removed"


class RFIDHandler:
    """
    RFID card reader handler using RC522 module.

    Monitors for card placement and removal, calling registered
    callbacks when events occur.

    Supports mock mode for development on systems without RFID hardware.
    """

    # GPIO pin for RFID reset (GPIO27 = Pin 13, avoids conflict with e-ink display)
    RST_PIN = 27

    def __init__(self, mock_mode: bool = False):
        """
        Initialize the RFID handler.

        Args:
            mock_mode: If True, use mock RFID for testing without hardware
        """
        self._mock_mode = mock_mode
        self._reader = None
        self._mfrc522 = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._current_card_id: Optional[str] = None
        self._on_card_placed: Optional[Callable[[str], None]] = None
        self._on_card_removed: Optional[Callable[[str], None]] = None

        # Debounce settings
        self._debounce_time = 0.3  # seconds
        self._last_read_time = 0
        self._consecutive_no_card = 0
        self._removal_threshold = 3  # consecutive no-card reads before removal

        # Poll interval
        self._poll_interval = 0.1  # seconds between reads

        # Mock mode state
        self._mock_card_id: Optional[str] = None

        if not mock_mode:
            self._init_reader()

    def _init_reader(self):
        """Initialize the MFRC522 reader."""
        try:
            from mfrc522 import MFRC522
            # Use custom RST pin (GPIO27) to avoid conflict with e-ink display DC pin
            self._mfrc522 = MFRC522(rst=self.RST_PIN)
            logger.info(f"RFID reader initialized (RST=GPIO{self.RST_PIN})")
        except ImportError:
            logger.warning("mfrc522 library not available - falling back to mock mode")
            self._mock_mode = True
        except Exception as e:
            logger.error(f"Failed to initialize RFID reader: {e}")
            logger.warning("Falling back to mock mode")
            self._mock_mode = True

    @property
    def current_card_id(self) -> Optional[str]:
        """Get the ID of the currently present card, or None if no card."""
        return self._current_card_id

    @property
    def has_card(self) -> bool:
        """Check if a card is currently present."""
        return self._current_card_id is not None

    @property
    def is_running(self) -> bool:
        """Check if the handler is actively monitoring."""
        return self._running

    def on_card_placed(self, callback: Callable[[str], None]):
        """
        Register a callback for card placement events.

        Args:
            callback: Function that takes the card ID as argument
        """
        self._on_card_placed = callback

    def on_card_removed(self, callback: Callable[[str], None]):
        """
        Register a callback for card removal events.

        Args:
            callback: Function that takes the removed card ID as argument
        """
        self._on_card_removed = callback

    def start(self):
        """Start monitoring for RFID cards in a background thread."""
        if self._running:
            logger.warning("RFID handler already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"RFID monitoring started (mock_mode={self._mock_mode})")

    def stop(self):
        """Stop monitoring for RFID cards."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("RFID monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop - runs in background thread."""
        while self._running:
            try:
                card_id = self._read_card()
                self._process_read(card_id)
            except Exception as e:
                logger.error(f"Error in RFID monitor loop: {e}")

            time.sleep(self._poll_interval)

    def _read_card(self) -> Optional[str]:
        """
        Attempt to read a card.

        Returns:
            Card ID as hex string, or None if no card present
        """
        if self._mock_mode:
            return self._mock_card_id

        if not self._mfrc522:
            return None

        try:
            # Request card presence
            (status, _) = self._mfrc522.Request(self._mfrc522.PICC_REQIDL)

            if status != self._mfrc522.MI_OK:
                return None

            # Get card UID
            (status, uid) = self._mfrc522.Anticoll()

            if status == self._mfrc522.MI_OK and uid:
                # Convert UID bytes to hex string
                uid_int = int.from_bytes(bytes(uid), 'big')
                return format(uid_int, 'x')

            return None

        except Exception as e:
            logger.debug(f"Card read error: {e}")
            return None

    def _process_read(self, card_id: Optional[str]):
        """Process a card read result and trigger events if needed."""
        current_time = time.time()

        if card_id:
            # Card detected
            self._consecutive_no_card = 0

            if self._current_card_id != card_id:
                # New card or different card
                if self._current_card_id is not None:
                    # Different card - first trigger removal of old card
                    self._trigger_removal(self._current_card_id)

                # Debounce new card detection
                if current_time - self._last_read_time >= self._debounce_time:
                    self._current_card_id = card_id
                    self._last_read_time = current_time
                    self._trigger_placement(card_id)
        else:
            # No card detected
            if self._current_card_id is not None:
                self._consecutive_no_card += 1

                # Only trigger removal after several consecutive no-card reads
                if self._consecutive_no_card >= self._removal_threshold:
                    removed_id = self._current_card_id
                    self._current_card_id = None
                    self._trigger_removal(removed_id)

    def _trigger_placement(self, card_id: str):
        """Trigger the card placement callback."""
        logger.info(f"Card placed: {card_id}")
        if self._on_card_placed:
            try:
                self._on_card_placed(card_id)
            except Exception as e:
                logger.error(f"Error in card placement callback: {e}")

    def _trigger_removal(self, card_id: str):
        """Trigger the card removal callback."""
        logger.info(f"Card removed: {card_id}")
        self._consecutive_no_card = 0
        if self._on_card_removed:
            try:
                self._on_card_removed(card_id)
            except Exception as e:
                logger.error(f"Error in card removal callback: {e}")

    # Mock mode methods for testing

    def mock_place_card(self, card_id: str):
        """
        Simulate placing a card (mock mode only).

        Args:
            card_id: The card ID to simulate
        """
        if not self._mock_mode:
            logger.warning("mock_place_card called but not in mock mode")
            return
        self._mock_card_id = card_id
        logger.debug(f"Mock: card {card_id} placed on reader")

    def mock_remove_card(self):
        """Simulate removing a card (mock mode only)."""
        if not self._mock_mode:
            logger.warning("mock_remove_card called but not in mock mode")
            return
        self._mock_card_id = None
        logger.debug("Mock: card removed from reader")

    def cleanup(self):
        """Clean up resources."""
        self.stop()
        if self._reader and hasattr(self._reader, 'READER'):
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False

"""
Display Manager Module for TaleTiles Audiobook Player

Supports multiple display types:
- Waveshare 2.13" e-ink display
- 16x2 Character LCD (HD44780 compatible)
- Mock mode for development without hardware
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class PlaybackStatus(Enum):
    """Playback status indicators."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    LOADING = "loading"


@dataclass
class DisplayState:
    """Current state to be displayed."""
    title: str = ""
    chapter_current: int = 0
    chapter_total: int = 0
    chapter_title: str = ""
    position_seconds: float = 0
    duration_seconds: float = 0
    time_remaining_seconds: float = 0
    volume: int = 75
    status: PlaybackStatus = PlaybackStatus.STOPPED
    message: str = ""  # For status messages like "Ready", "Unknown card", etc.

    def __eq__(self, other):
        if not isinstance(other, DisplayState):
            return False
        return (
            self.title == other.title and
            self.chapter_current == other.chapter_current and
            self.chapter_total == other.chapter_total and
            self.volume == other.volume and
            self.status == other.status and
            self.message == other.message
        )


class BaseDisplay(ABC):
    """Abstract base class for display implementations."""

    @abstractmethod
    def init_hardware(self) -> bool:
        """Initialize the display hardware. Returns True on success."""
        pass

    @abstractmethod
    def render(self, state: DisplayState):
        """Render the state to the display."""
        pass

    @abstractmethod
    def clear(self):
        """Clear the display."""
        pass

    @abstractmethod
    def cleanup(self):
        """Clean up display resources."""
        pass

    def _format_time(self, seconds: float) -> str:
        """Format seconds as human-readable time."""
        if seconds < 0:
            return "0m"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if hours > 0:
            return f"{hours}h{minutes}m"
        return f"{minutes}m"


class MockDisplay(BaseDisplay):
    """Console output display for development/testing."""

    def init_hardware(self) -> bool:
        logger.info("Mock display initialized")
        return True

    def render(self, state: DisplayState):
        width = 40

        if state.message:
            line1 = state.message[:width]
        elif state.title:
            line1 = state.title[:width]
        else:
            line1 = "TaleTiles"

        if state.chapter_total > 0:
            remaining = self._format_time(state.time_remaining_seconds)
            line2 = f"Ch {state.chapter_current}/{state.chapter_total}  {remaining} left"
        else:
            line2 = ""

        if state.chapter_title and not state.message:
            line3 = state.chapter_title[:width]
        else:
            line3 = ""

        status_icon = {
            PlaybackStatus.STOPPED: "■",
            PlaybackStatus.PLAYING: "▶",
            PlaybackStatus.PAUSED: "⏸",
            PlaybackStatus.LOADING: "◌",
        }.get(state.status, "?")

        status_text = state.status.value.capitalize()
        line4 = f"{status_icon} {status_text:<12} Vol {state.volume}%"

        border = "─" * (width + 2)
        print(f"\n┌{border}┐")
        print(f"│ {line1:<{width}} │")
        print(f"│ {line2:<{width}} │")
        print(f"│ {line3:<{width}} │")
        print(f"│ {line4:<{width}} │")
        print(f"└{border}┘\n")

    def clear(self):
        print("\n[Display cleared]\n")

    def cleanup(self):
        pass


class EinkDisplay(BaseDisplay):
    """Waveshare 2.13" V4 e-ink display implementation."""

    DISPLAY_WIDTH = 250
    DISPLAY_HEIGHT = 122

    def __init__(self):
        self._display = None
        self._image = None
        self._draw = None
        self._font = None
        self._font_small = None
        self._font_large = None

    def init_hardware(self) -> bool:
        try:
            from waveshare_epd import epd2in13_V4
            from PIL import Image, ImageDraw, ImageFont

            self._display = epd2in13_V4.EPD()
            self._display.init()
            self._display.Clear(0xFF)

            self._image = Image.new('1', (self.DISPLAY_WIDTH, self.DISPLAY_HEIGHT), 255)
            self._draw = ImageDraw.Draw(self._image)

            try:
                self._font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
                self._font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
                self._font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
            except OSError:
                self._font_large = ImageFont.load_default()
                self._font = ImageFont.load_default()
                self._font_small = ImageFont.load_default()

            logger.info("E-ink display initialized")
            return True

        except ImportError:
            logger.warning("Waveshare library not available")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize e-ink display: {e}")
            return False

    def render(self, state: DisplayState):
        if not self._display or not self._draw:
            return

        try:
            self._draw.rectangle((0, 0, self.DISPLAY_WIDTH, self.DISPLAY_HEIGHT), fill=255)

            y = 5

            if state.message:
                text = state.message
            elif state.title:
                text = self._truncate_text(state.title, self.DISPLAY_WIDTH - 10, self._font_large)
            else:
                text = "TaleTiles"

            self._draw.text((5, y), text, font=self._font_large, fill=0)
            y += 25

            if state.chapter_total > 0:
                remaining = self._format_time(state.time_remaining_seconds)
                chapter_text = f"Ch {state.chapter_current}/{state.chapter_total}  |  {remaining} left"
                self._draw.text((5, y), chapter_text, font=self._font, fill=0)
                y += 20

            if state.chapter_title and not state.message:
                chapter_title = self._truncate_text(state.chapter_title, self.DISPLAY_WIDTH - 10, self._font_small)
                self._draw.text((5, y), chapter_title, font=self._font_small, fill=0)
                y += 18

            y = self.DISPLAY_HEIGHT - 25
            self._draw.line((5, y - 5, self.DISPLAY_WIDTH - 5, y - 5), fill=0, width=1)

            status_icons = {
                PlaybackStatus.STOPPED: "■",
                PlaybackStatus.PLAYING: "▶",
                PlaybackStatus.PAUSED: "II",
                PlaybackStatus.LOADING: "...",
            }
            status_icon = status_icons.get(state.status, "?")
            status_text = f"{status_icon} {state.status.value.capitalize()}"
            self._draw.text((5, y), status_text, font=self._font, fill=0)

            volume_text = f"Vol {state.volume}%"
            vol_width = self._font.getlength(volume_text) if hasattr(self._font, 'getlength') else 60
            self._draw.text((self.DISPLAY_WIDTH - vol_width - 5, y), volume_text, font=self._font, fill=0)

            self._display.displayPartial(self._display.getbuffer(self._image))

        except Exception as e:
            logger.error(f"Error rendering to e-ink: {e}")

    def _truncate_text(self, text: str, max_width: int, font) -> str:
        if not hasattr(font, 'getlength'):
            max_chars = max_width // 8
            if len(text) > max_chars:
                return text[:max_chars - 3] + "..."
            return text

        if font.getlength(text) <= max_width:
            return text

        for i in range(len(text), 0, -1):
            truncated = text[:i] + "..."
            if font.getlength(truncated) <= max_width:
                return truncated

        return "..."

    def clear(self):
        if self._display:
            try:
                self._display.Clear(0xFF)
            except Exception as e:
                logger.debug(f"Error clearing e-ink: {e}")

    def cleanup(self):
        if self._display:
            try:
                self._display.Clear(0xFF)
                self._display.sleep()
            except Exception as e:
                logger.debug(f"Error cleaning up e-ink: {e}")


class LCD1602Display(BaseDisplay):
    """16x2 Character LCD display implementation (HD44780 compatible, 4-bit mode)."""

    def __init__(self, rs_pin: int = 16, e_pin: int = 18,
                 d4_pin: int = 20, d5_pin: int = 21,
                 d6_pin: int = 22, d7_pin: int = 23):
        self._rs = rs_pin
        self._e = e_pin
        self._data_pins = [d4_pin, d5_pin, d6_pin, d7_pin]
        self._lcd = None
        self._last_lines = ["", ""]

    def init_hardware(self) -> bool:
        try:
            from RPLCD.gpio import CharLCD
            import RPi.GPIO as GPIO

            GPIO.setwarnings(False)

            self._lcd = CharLCD(
                numbering_mode=GPIO.BCM,
                cols=16,
                rows=2,
                pin_rs=self._rs,
                pin_e=self._e,
                pins_data=self._data_pins,
                auto_linebreaks=False
            )

            self._lcd.clear()
            logger.info(f"LCD 1602 initialized (RS={self._rs}, E={self._e}, D4-D7={self._data_pins})")
            return True

        except ImportError:
            logger.warning("RPLCD library not available - install with: pip install RPLCD")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize LCD: {e}")
            return False

    def render(self, state: DisplayState):
        if not self._lcd:
            return

        try:
            # Line 1: Title/message (or status icon + truncated title)
            if state.message:
                line1 = state.message[:16]
            elif state.title:
                status_char = {
                    PlaybackStatus.STOPPED: " ",
                    PlaybackStatus.PLAYING: ">",
                    PlaybackStatus.PAUSED: "=",
                    PlaybackStatus.LOADING: "*",
                }.get(state.status, " ")
                line1 = f"{status_char}{state.title[:15]}"
            else:
                line1 = "TaleTiles"

            # Line 2: Chapter info and volume (or time remaining)
            if state.chapter_total > 0:
                remaining = self._format_time(state.time_remaining_seconds)
                # Format: "C01/12  -2h30m" or "C1/5 V75 -30m"
                ch_str = f"C{state.chapter_current}/{state.chapter_total}"
                vol_str = f"V{state.volume}"
                # Fit what we can
                line2 = f"{ch_str} {vol_str} -{remaining}"
                if len(line2) > 16:
                    line2 = f"{ch_str} -{remaining}"
                if len(line2) > 16:
                    line2 = f"Ch{state.chapter_current} -{remaining}"
            else:
                line2 = f"Vol: {state.volume}%"

            # Pad to 16 chars and only update if changed
            line1 = line1[:16].ljust(16)
            line2 = line2[:16].ljust(16)

            if line1 != self._last_lines[0] or line2 != self._last_lines[1]:
                self._lcd.home()
                self._lcd.write_string(line1)
                self._lcd.cursor_pos = (1, 0)
                self._lcd.write_string(line2)
                self._last_lines = [line1, line2]

        except Exception as e:
            logger.error(f"Error rendering to LCD: {e}")

    def clear(self):
        if self._lcd:
            try:
                self._lcd.clear()
                self._last_lines = ["", ""]
            except Exception as e:
                logger.debug(f"Error clearing LCD: {e}")

    def cleanup(self):
        if self._lcd:
            try:
                self._lcd.clear()
                self._lcd.close(clear=True)
            except Exception as e:
                logger.debug(f"Error cleaning up LCD: {e}")


class DisplayManager:
    """
    Manages the display for the audiobook player.

    Supports:
    - Waveshare 2.13" e-ink display
    - 16x2 Character LCD (HD44780)
    - Console mock mode (for development)
    """

    def __init__(self, mock_mode: bool = False, display_type: str = "eink",
                 lcd_config: Optional[dict] = None):
        """
        Initialize the display manager.

        Args:
            mock_mode: If True, output to console instead of hardware
            display_type: "eink" or "lcd1602"
            lcd_config: Optional dict with LCD pin configuration
        """
        self._mock_mode = mock_mode
        self._display_type = display_type
        self._display: Optional[BaseDisplay] = None

        self._current_state = DisplayState()
        self._pending_state: Optional[DisplayState] = None
        self._update_lock = threading.Lock()
        self._update_thread: Optional[threading.Thread] = None
        self._running = False

        # Update throttling (shorter for LCD since it updates faster)
        if display_type == "lcd1602":
            self._min_update_interval = 0.5
        else:
            self._min_update_interval = 2.0
        self._last_update_time = 0

        # Initialize display
        if mock_mode:
            self._display = MockDisplay()
            self._display.init_hardware()
            logger.info("Display manager running in mock mode")
        else:
            self._init_display(display_type, lcd_config or {})

    def _init_display(self, display_type: str, lcd_config: dict):
        """Initialize the hardware display."""
        if display_type == "lcd1602":
            self._display = LCD1602Display(
                rs_pin=lcd_config.get("lcd_rs", 16),
                e_pin=lcd_config.get("lcd_e", 18),
                d4_pin=lcd_config.get("lcd_d4", 20),
                d5_pin=lcd_config.get("lcd_d5", 21),
                d6_pin=lcd_config.get("lcd_d6", 22),
                d7_pin=lcd_config.get("lcd_d7", 23),
            )
        else:
            self._display = EinkDisplay()

        if not self._display.init_hardware():
            logger.warning(f"Failed to initialize {display_type} display, falling back to mock mode")
            self._mock_mode = True
            self._display = MockDisplay()
            self._display.init_hardware()

    def start(self):
        """Start the display update thread."""
        if self._running:
            return

        self._running = True
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
        logger.info("Display manager started")

    def stop(self):
        """Stop the display manager."""
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=2.0)
            self._update_thread = None

        if self._display and not self._mock_mode:
            self._display.clear()

        logger.info("Display manager stopped")

    def _update_loop(self):
        """Background thread for updating the display."""
        while self._running:
            with self._update_lock:
                if self._pending_state and self._pending_state != self._current_state:
                    now = time.time()
                    if now - self._last_update_time >= self._min_update_interval:
                        self._render(self._pending_state)
                        self._current_state = self._pending_state
                        self._pending_state = None
                        self._last_update_time = now

            time.sleep(0.1)

    def update(self, state: DisplayState):
        """Queue a display update."""
        with self._update_lock:
            self._pending_state = state

        # Force immediate update for important state changes
        if (state.status != self._current_state.status or
            state.title != self._current_state.title or
            state.message != self._current_state.message):
            self._force_update()

    def _force_update(self):
        """Force an immediate display update."""
        with self._update_lock:
            if self._pending_state:
                self._render(self._pending_state)
                self._current_state = self._pending_state
                self._pending_state = None
                self._last_update_time = time.time()

    def _render(self, state: DisplayState):
        """Render the state to the display."""
        if self._display:
            self._display.render(state)

    # Convenience methods for common updates

    def show_ready(self):
        """Show ready state."""
        self.update(DisplayState(
            message="Ready",
            status=PlaybackStatus.STOPPED
        ))

    def show_loading(self, title: str):
        """Show loading state."""
        self.update(DisplayState(
            title=title,
            message=f"Loading: {title}"[:16] if self._display_type == "lcd1602" else f"Loading: {title}",
            status=PlaybackStatus.LOADING
        ))

    def show_error(self, message: str):
        """Show error message."""
        self.update(DisplayState(
            message=message,
            status=PlaybackStatus.STOPPED
        ))

    def show_unknown_card(self, card_id: str):
        """Show unknown card message."""
        short_id = card_id[:8] + "..." if len(card_id) > 8 else card_id
        if self._display_type == "lcd1602":
            self.update(DisplayState(
                message=f"Unknown: {short_id}"[:16],
                status=PlaybackStatus.STOPPED
            ))
        else:
            self.update(DisplayState(
                message=f"Unknown card: {short_id}",
                status=PlaybackStatus.STOPPED
            ))

    def show_playing(self, title: str, chapter_num: int, chapter_total: int,
                     chapter_title: str, time_remaining: float, volume: int):
        """Show playing state."""
        self.update(DisplayState(
            title=title,
            chapter_current=chapter_num,
            chapter_total=chapter_total,
            chapter_title=chapter_title,
            time_remaining_seconds=time_remaining,
            volume=volume,
            status=PlaybackStatus.PLAYING
        ))

    def show_paused(self, title: str, chapter_num: int, chapter_total: int,
                    chapter_title: str, time_remaining: float, volume: int):
        """Show paused state."""
        self.update(DisplayState(
            title=title,
            chapter_current=chapter_num,
            chapter_total=chapter_total,
            chapter_title=chapter_title,
            time_remaining_seconds=time_remaining,
            volume=volume,
            status=PlaybackStatus.PAUSED
        ))

    def cleanup(self):
        """Clean up resources."""
        self.stop()
        if self._display:
            self._display.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False

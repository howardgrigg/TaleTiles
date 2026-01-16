"""
Button Handler Module for TaleTiles Audiobook Player

Handles physical button input via GPIO:
- 5 buttons: Play/Pause, Vol Up, Vol Down, Skip Back, Skip Forward
- Debouncing for reliable detection
- Single/double-click detection for Skip buttons
- Mock mode for development without hardware
"""

import logging
import threading
import time
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class Button(Enum):
    """Button identifiers."""
    PLAY_PAUSE = "play_pause"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    SKIP_BACK = "skip_back"
    SKIP_FORWARD = "skip_forward"


class ButtonAction(Enum):
    """Button action types."""
    SINGLE = "single"
    DOUBLE = "double"


# GPIO pin assignments (active low with pull-up)
DEFAULT_PIN_MAP = {
    Button.PLAY_PAUSE: 5,    # GPIO5, Pin 29
    Button.VOLUME_UP: 6,     # GPIO6, Pin 31
    Button.VOLUME_DOWN: 12,  # GPIO12, Pin 32
    Button.SKIP_BACK: 13,    # GPIO13, Pin 33
    Button.SKIP_FORWARD: 19, # GPIO19, Pin 35
}

# Buttons that support double-click
DOUBLE_CLICK_BUTTONS = {Button.SKIP_BACK, Button.SKIP_FORWARD}

# Timing constants
DEBOUNCE_TIME = 0.05        # 50ms debounce
DOUBLE_CLICK_TIMEOUT = 0.3  # 300ms window for double-click


class ButtonHandler:
    """
    Handles physical button input with debouncing and double-click detection.

    For Skip buttons: executes single-click action immediately, then cancels
    and executes double-click action if second press detected within timeout.
    """

    def __init__(self, mock_mode: bool = False, pin_map: Optional[dict] = None):
        """
        Initialize the button handler.

        Args:
            mock_mode: If True, use keyboard input instead of GPIO
            pin_map: Custom GPIO pin assignments (default: DEFAULT_PIN_MAP)
        """
        self._mock_mode = mock_mode
        self._pin_map = pin_map or DEFAULT_PIN_MAP
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Callbacks: button -> {action -> callback}
        self._callbacks: dict[Button, dict[ButtonAction, Callable]] = {
            button: {} for button in Button
        }

        # Double-click state
        self._pending_single: dict[Button, float] = {}  # button -> timestamp
        self._double_click_timers: dict[Button, threading.Timer] = {}

        # GPIO state
        self._gpio_initialized = False

        if not mock_mode:
            self._init_gpio()

    def _init_gpio(self):
        """Initialize GPIO pins."""
        try:
            import RPi.GPIO as GPIO

            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            for button, pin in self._pin_map.items():
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(
                    pin,
                    GPIO.FALLING,
                    callback=lambda channel, b=button: self._on_gpio_press(b),
                    bouncetime=int(DEBOUNCE_TIME * 1000)
                )
                logger.debug(f"Configured {button.value} on GPIO{pin}")

            self._gpio_initialized = True
            logger.info("GPIO buttons initialized")

        except ImportError:
            logger.warning("RPi.GPIO not available - falling back to mock mode")
            self._mock_mode = True
        except Exception as e:
            logger.error(f"Failed to initialize GPIO: {e}")
            logger.warning("Falling back to mock mode")
            self._mock_mode = True

    def _on_gpio_press(self, button: Button):
        """Handle GPIO button press event."""
        self._handle_press(button)

    def _handle_press(self, button: Button):
        """Handle a button press with double-click detection."""
        now = time.time()

        if button in DOUBLE_CLICK_BUTTONS:
            # Check if this is a double-click
            if button in self._pending_single:
                elapsed = now - self._pending_single[button]
                if elapsed < DOUBLE_CLICK_TIMEOUT:
                    # Double-click detected - cancel pending single
                    self._cancel_pending_single(button)
                    self._execute_callback(button, ButtonAction.DOUBLE)
                    return

            # First click - execute single immediately, but set up for potential double
            self._execute_callback(button, ButtonAction.SINGLE)
            self._pending_single[button] = now

            # Set timer to clear pending state
            if button in self._double_click_timers:
                self._double_click_timers[button].cancel()

            timer = threading.Timer(
                DOUBLE_CLICK_TIMEOUT,
                lambda: self._clear_pending_single(button)
            )
            timer.daemon = True
            timer.start()
            self._double_click_timers[button] = timer

        else:
            # Simple button - just execute
            self._execute_callback(button, ButtonAction.SINGLE)

    def _cancel_pending_single(self, button: Button):
        """Cancel a pending single-click action."""
        if button in self._pending_single:
            del self._pending_single[button]
        if button in self._double_click_timers:
            self._double_click_timers[button].cancel()
            del self._double_click_timers[button]

    def _clear_pending_single(self, button: Button):
        """Clear pending single-click state after timeout."""
        if button in self._pending_single:
            del self._pending_single[button]
        if button in self._double_click_timers:
            del self._double_click_timers[button]

    def _execute_callback(self, button: Button, action: ButtonAction):
        """Execute the registered callback for a button action."""
        callbacks = self._callbacks.get(button, {})
        callback = callbacks.get(action)

        if callback:
            logger.debug(f"Button {button.value} {action.value} click")
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in button callback: {e}")
        else:
            logger.debug(f"No callback for {button.value} {action.value}")

    def on_play_pause(self, callback: Callable):
        """Register callback for Play/Pause button."""
        self._callbacks[Button.PLAY_PAUSE][ButtonAction.SINGLE] = callback

    def on_volume_up(self, callback: Callable):
        """Register callback for Volume Up button."""
        self._callbacks[Button.VOLUME_UP][ButtonAction.SINGLE] = callback

    def on_volume_down(self, callback: Callable):
        """Register callback for Volume Down button."""
        self._callbacks[Button.VOLUME_DOWN][ButtonAction.SINGLE] = callback

    def on_skip_back(self, callback: Callable):
        """Register callback for Skip Back single-click (30 seconds)."""
        self._callbacks[Button.SKIP_BACK][ButtonAction.SINGLE] = callback

    def on_skip_back_double(self, callback: Callable):
        """Register callback for Skip Back double-click (previous chapter)."""
        self._callbacks[Button.SKIP_BACK][ButtonAction.DOUBLE] = callback

    def on_skip_forward(self, callback: Callable):
        """Register callback for Skip Forward single-click (30 seconds)."""
        self._callbacks[Button.SKIP_FORWARD][ButtonAction.SINGLE] = callback

    def on_skip_forward_double(self, callback: Callable):
        """Register callback for Skip Forward double-click (next chapter)."""
        self._callbacks[Button.SKIP_FORWARD][ButtonAction.DOUBLE] = callback

    def start(self):
        """Start listening for button events."""
        if self._running:
            return

        self._running = True

        if self._mock_mode:
            self._thread = threading.Thread(target=self._mock_input_loop, daemon=True)
            self._thread.start()
            logger.info("Button handler started (mock mode - keyboard input)")
        else:
            logger.info("Button handler started (GPIO mode)")

    def stop(self):
        """Stop listening for button events."""
        self._running = False

        # Cancel any pending timers
        for timer in self._double_click_timers.values():
            timer.cancel()
        self._double_click_timers.clear()

        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

        logger.info("Button handler stopped")

    def _mock_input_loop(self):
        """Mock input loop using keyboard (for testing)."""
        # This is handled externally in mock mode
        # The main player will call simulate_press() based on keyboard input
        while self._running:
            time.sleep(0.1)

    def simulate_press(self, button: Button):
        """
        Simulate a button press (for mock mode or testing).

        Args:
            button: The button to simulate
        """
        self._handle_press(button)

    def cleanup(self):
        """Clean up resources."""
        self.stop()

        if self._gpio_initialized:
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


# Key mappings for mock/keyboard mode
KEYBOARD_MAP = {
    ' ': Button.PLAY_PAUSE,      # Space = Play/Pause
    '+': Button.VOLUME_UP,       # + = Volume Up
    '=': Button.VOLUME_UP,       # = = Volume Up (unshifted +)
    '-': Button.VOLUME_DOWN,     # - = Volume Down
    ',': Button.SKIP_BACK,       # , = Skip Back
    '<': Button.SKIP_BACK,       # < = Skip Back
    '.': Button.SKIP_FORWARD,    # . = Skip Forward
    '>': Button.SKIP_FORWARD,    # > = Skip Forward
}

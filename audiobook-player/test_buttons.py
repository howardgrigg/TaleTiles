#!/usr/bin/env python3
"""
Test script for TaleTiles Button Handler - Phase 4 Validation

Tests button handling including double-click detection.

Usage:
    python test_buttons.py

Controls:
    Space   - Play/Pause
    + / =   - Volume Up
    -       - Volume Down
    , / <   - Skip Back (double-tap for previous chapter)
    . / >   - Skip Forward (double-tap for next chapter)
    q       - Quit
"""

import sys
import time
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.button_handler import ButtonHandler, Button, KEYBOARD_MAP


def main():
    print("\n" + "=" * 60)
    print("TaleTiles Button Handler Test")
    print("=" * 60)
    print("\nControls:")
    print("  Space     Play/Pause")
    print("  + or =    Volume Up")
    print("  -         Volume Down")
    print("  , or <    Skip Back (double-tap: prev chapter)")
    print("  . or >    Skip Forward (double-tap: next chapter)")
    print("  q         Quit")
    print("\n" + "=" * 60 + "\n")

    actions = []

    def log_action(name: str):
        def callback():
            timestamp = time.strftime("%H:%M:%S")
            actions.append(name)
            print(f"  [{timestamp}] {name}")
        return callback

    handler = ButtonHandler(mock_mode=True)

    # Register callbacks
    handler.on_play_pause(log_action("PLAY/PAUSE"))
    handler.on_volume_up(log_action("VOLUME UP"))
    handler.on_volume_down(log_action("VOLUME DOWN"))
    handler.on_skip_back(log_action("SKIP BACK 30s"))
    handler.on_skip_back_double(log_action("PREVIOUS CHAPTER"))
    handler.on_skip_forward(log_action("SKIP FORWARD 30s"))
    handler.on_skip_forward_double(log_action("NEXT CHAPTER"))

    handler.start()
    print("Button handler started. Press keys to test...\n")

    try:
        while True:
            # Read single character
            char = read_char()

            if char is None:
                continue

            if char.lower() == 'q':
                break

            # Map key to button
            button = KEYBOARD_MAP.get(char)
            if button:
                handler.simulate_press(button)
            else:
                print(f"  Unknown key: {repr(char)}")

    except KeyboardInterrupt:
        pass

    handler.cleanup()

    print("\n" + "=" * 60)
    print(f"Session ended. {len(actions)} actions recorded:")
    for action in actions[-10:]:  # Show last 10
        print(f"  - {action}")
    print("=" * 60 + "\n")


def read_char():
    """Read a single character from stdin without requiring Enter."""
    try:
        import tty
        import termios

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
    except Exception:
        # Fallback for systems without tty support
        return input("> ")[:1] if input else None


if __name__ == '__main__':
    main()

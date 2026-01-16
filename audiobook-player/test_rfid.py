#!/usr/bin/env python3
"""
Test script for TaleTiles RFID Handler - Phase 2 Validation

On Raspberry Pi: Tests real RC522 RFID reader hardware
On other systems: Uses mock mode with keyboard simulation

Usage:
    python test_rfid.py [--real]

Options:
    --real    Force real hardware mode (will fail if not on Pi)
"""

import sys
import time
import logging
import platform
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))
from lib.rfid_handler import RFIDHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)


def test_mock_mode():
    """Test RFID handler in mock mode with simulated cards."""
    print("\n" + "=" * 60)
    print("RFID Handler Test - Mock Mode")
    print("=" * 60)
    print("\nThis simulates RFID card events for testing without hardware.")
    print("Commands:")
    print("  1-5     - Place card with ID 'card1' through 'card5'")
    print("  r       - Remove current card")
    print("  s       - Show current status")
    print("  q       - Quit")
    print("=" * 60 + "\n")

    cards_seen = []

    def on_placed(card_id):
        print(f"  >>> CARD PLACED: {card_id}")
        if card_id not in cards_seen:
            cards_seen.append(card_id)

    def on_removed(card_id):
        print(f"  <<< CARD REMOVED: {card_id}")

    with RFIDHandler(mock_mode=True) as rfid:
        rfid.on_card_placed(on_placed)
        rfid.on_card_removed(on_removed)
        rfid.start()

        print("RFID handler started in mock mode")
        print("Waiting for commands...\n")

        while True:
            try:
                cmd = input("> ").strip().lower()

                if cmd == 'q':
                    break
                elif cmd == 'r':
                    rfid.mock_remove_card()
                    print("Simulating card removal...")
                elif cmd == 's':
                    print(f"Current card: {rfid.current_card_id or 'None'}")
                    print(f"Cards seen: {cards_seen}")
                elif cmd in ['1', '2', '3', '4', '5']:
                    card_id = f"card{cmd}"
                    rfid.mock_place_card(card_id)
                    print(f"Simulating card placement: {card_id}")
                elif cmd:
                    # Treat any other input as a custom card ID
                    rfid.mock_place_card(cmd)
                    print(f"Simulating card placement: {cmd}")

                # Give the monitor thread time to process
                time.sleep(0.5)

            except KeyboardInterrupt:
                print("\nInterrupted")
                break

    print(f"\nSession complete. Cards seen: {cards_seen}")


def test_real_mode():
    """Test RFID handler with real RC522 hardware."""
    print("\n" + "=" * 60)
    print("RFID Handler Test - Real Hardware Mode")
    print("=" * 60)
    print("\nPlace RFID cards on the reader to test detection.")
    print("Press Ctrl+C to exit.")
    print("=" * 60 + "\n")

    cards_seen = {}

    def on_placed(card_id):
        count = cards_seen.get(card_id, 0) + 1
        cards_seen[card_id] = count
        print(f"  >>> CARD PLACED: {card_id} (seen {count} time(s))")

    def on_removed(card_id):
        print(f"  <<< CARD REMOVED: {card_id}")

    with RFIDHandler(mock_mode=False) as rfid:
        if rfid._mock_mode:
            print("WARNING: Fell back to mock mode (hardware not available)")
            print("Run with real hardware on Raspberry Pi\n")

        rfid.on_card_placed(on_placed)
        rfid.on_card_removed(on_removed)
        rfid.start()

        print("RFID handler started")
        print("Waiting for cards...\n")

        try:
            while True:
                time.sleep(1)
                # Periodic status
                if rfid.has_card:
                    print(f"  [Card present: {rfid.current_card_id}]", end='\r')
        except KeyboardInterrupt:
            print("\n\nStopping...")

    print(f"\nSession complete. Cards seen: {cards_seen}")


def main():
    # Detect if we should use real or mock mode
    force_real = '--real' in sys.argv

    # Check if we're likely on a Raspberry Pi
    is_pi = platform.machine().startswith('arm') or platform.machine() == 'aarch64'

    if force_real:
        print("Forcing real hardware mode...")
        test_real_mode()
    elif is_pi:
        print("Detected Raspberry Pi - using real hardware mode")
        print("(Use mock mode with: python test_rfid.py --mock)")
        test_real_mode()
    else:
        print(f"Not on Raspberry Pi ({platform.machine()}) - using mock mode")
        print("(Force real mode with: python test_rfid.py --real)")
        test_mock_mode()


if __name__ == '__main__':
    main()

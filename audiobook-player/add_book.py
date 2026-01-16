#!/usr/bin/env python3
"""
TaleTiles Audiobook Registration Helper

Register audiobooks with RFID cards for the TaleTiles player.

Usage:
    python add_book.py              # Interactive registration
    python add_book.py --list       # List all registered books
    python add_book.py --check      # Check for issues
    python add_book.py --remove     # Remove a registration
    python add_book.py --mock       # Use mock RFID for testing
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.rfid_handler import RFIDHandler
from lib.state_manager import StateManager


def find_audiobooks(audiobooks_path: Path) -> list[tuple[Path, str]]:
    """
    Find all audiobook folders.

    Returns list of (path, title) tuples.
    """
    audiobooks = []
    audio_extensions = {'.mp3', '.m4a', '.m4b', '.ogg', '.flac'}

    for item in audiobooks_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Check if folder contains audio files
            has_audio = any(
                f.suffix.lower() in audio_extensions
                for f in item.iterdir() if f.is_file()
            )
            if has_audio:
                # Try to get title from metadata
                title = get_audiobook_title(item)
                audiobooks.append((item, title))

    return sorted(audiobooks, key=lambda x: x[1].lower())


def get_audiobook_title(path: Path) -> str:
    """Get audiobook title from metadata or folder name."""
    metadata_path = path / "metadata" / "metadata.json"
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                title = metadata.get('title')
                if title:
                    return title
        except (json.JSONDecodeError, IOError):
            pass
    return path.name


def interactive_register(state: StateManager, audiobooks_path: Path, mock_rfid: bool):
    """Interactive audiobook registration."""
    print("\n" + "=" * 60)
    print("TaleTiles Audiobook Registration")
    print("=" * 60)

    # Find available audiobooks
    audiobooks = find_audiobooks(audiobooks_path)
    if not audiobooks:
        print(f"\nNo audiobooks found in {audiobooks_path}")
        print("Add audiobook folders containing MP3/M4B files.")
        return

    # Filter out already registered ones
    registered_paths = {Path(ab.path) for ab in state.get_all_audiobooks()}
    available = [(p, t) for p, t in audiobooks if p not in registered_paths]

    if not available:
        print("\nAll audiobooks are already registered!")
        return

    print(f"\nFound {len(available)} unregistered audiobook(s):\n")
    for i, (path, title) in enumerate(available):
        print(f"  {i + 1}. {title}")
        print(f"      {path.name}")

    print()

    # Select audiobook
    while True:
        choice = input("Select audiobook number (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(available):
                selected_path, selected_title = available[idx]
                break
            print("Invalid selection, try again.")
        except ValueError:
            print("Enter a number or 'q' to quit.")

    # Confirm or edit title
    print(f"\nSelected: {selected_title}")
    new_title = input(f"Display title [{selected_title}]: ").strip()
    if new_title:
        selected_title = new_title

    # Wait for RFID card
    print("\n" + "-" * 60)
    print("Place an RFID card on the reader...")
    print("-" * 60)

    card_id = wait_for_card(mock_rfid)
    if card_id is None:
        print("Cancelled.")
        return

    # Check if card is already registered
    existing = state.get_audiobook(card_id)
    if existing:
        print(f"\nThis card is already registered to: {existing.title}")
        confirm = input("Replace existing registration? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return

    # Register the audiobook
    state.register_audiobook(card_id, selected_path, selected_title)

    print("\n" + "=" * 60)
    print("Registration Complete!")
    print("=" * 60)
    print(f"  Card ID: {card_id}")
    print(f"  Title:   {selected_title}")
    print(f"  Path:    {selected_path}")
    print("=" * 60 + "\n")


def wait_for_card(mock_rfid: bool, timeout: float = 60) -> str | None:
    """Wait for an RFID card to be placed."""
    card_id = None
    card_event = []

    def on_placed(cid):
        card_event.append(cid)

    rfid = RFIDHandler(mock_mode=mock_rfid)
    rfid.on_card_placed(on_placed)
    rfid.start()

    if mock_rfid:
        print("(Mock mode - enter a card ID, or press Enter for 'testcard')")
        user_input = input("> ").strip()
        card_id = user_input if user_input else "testcard"
    else:
        start_time = time.time()
        while time.time() - start_time < timeout:
            if card_event:
                card_id = card_event[0]
                break
            time.sleep(0.1)

        if card_id is None:
            print("Timeout waiting for card.")

    rfid.cleanup()
    return card_id


def list_books(state: StateManager):
    """List all registered audiobooks."""
    audiobooks = state.get_all_audiobooks()

    print("\n" + "=" * 60)
    print("Registered Audiobooks")
    print("=" * 60)

    if not audiobooks:
        print("\nNo audiobooks registered yet.")
        print("Use 'python add_book.py' to register audiobooks.\n")
        return

    for i, ab in enumerate(audiobooks):
        exists = Path(ab.path).exists()
        status = "OK" if exists else "MISSING"

        print(f"\n{i + 1}. {ab.title}")
        print(f"   Card ID: {ab.card_id}")
        print(f"   Path:    {ab.path}")
        print(f"   Status:  {status}")
        if ab.last_played:
            print(f"   Last played: {ab.last_played[:10]}")
        if ab.position_seconds > 0:
            mins = int(ab.position_seconds // 60)
            secs = int(ab.position_seconds % 60)
            print(f"   Position: File {ab.current_file_index + 1}, {mins}:{secs:02d}")

    print("\n" + "=" * 60 + "\n")


def check_issues(state: StateManager):
    """Check for configuration issues."""
    print("\n" + "=" * 60)
    print("Configuration Check")
    print("=" * 60)

    missing = state.validate_paths()

    if not missing:
        print("\nAll registered audiobooks are accessible.")
    else:
        print(f"\nFound {len(missing)} issue(s):\n")
        for card_id, title, path in missing:
            print(f"  MISSING: {title}")
            print(f"           Card: {card_id}")
            print(f"           Path: {path}\n")

    print("=" * 60 + "\n")


def remove_registration(state: StateManager, mock_rfid: bool):
    """Remove an audiobook registration."""
    audiobooks = state.get_all_audiobooks()

    if not audiobooks:
        print("\nNo audiobooks registered.\n")
        return

    print("\n" + "=" * 60)
    print("Remove Audiobook Registration")
    print("=" * 60)
    print("\nRegistered audiobooks:\n")

    for i, ab in enumerate(audiobooks):
        print(f"  {i + 1}. {ab.title} (Card: {ab.card_id[:8]}...)")

    print()

    while True:
        choice = input("Select number to remove (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(audiobooks):
                selected = audiobooks[idx]
                break
            print("Invalid selection, try again.")
        except ValueError:
            print("Enter a number or 'q' to quit.")

    confirm = input(f"\nRemove '{selected.title}'? [y/N]: ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return

    state.unregister_audiobook(selected.card_id)
    print(f"\nRemoved: {selected.title}\n")


def main():
    parser = argparse.ArgumentParser(description='TaleTiles Audiobook Registration')
    parser.add_argument('--list', action='store_true',
                        help='List all registered audiobooks')
    parser.add_argument('--check', action='store_true',
                        help='Check for configuration issues')
    parser.add_argument('--remove', action='store_true',
                        help='Remove a registration')
    parser.add_argument('--mock', action='store_true',
                        help='Use mock RFID for testing')
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

    # Load state
    state = StateManager(config_path)

    try:
        if args.list:
            list_books(state)
        elif args.check:
            check_issues(state)
        elif args.remove:
            remove_registration(state, args.mock)
        else:
            interactive_register(state, audiobooks_path, args.mock)
    finally:
        state.save()


if __name__ == '__main__':
    main()

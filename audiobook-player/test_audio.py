#!/usr/bin/env python3
"""
Test script for TaleTiles Audio Player - Phase 1 Validation

Interactive CLI to test audio playback functionality:
- Load audiobook from folder
- Play/pause
- Seek forward/back
- Chapter navigation
- Volume control
- Position tracking

Usage:
    python test_audio.py [audiobook_path]

If no path provided, will look for audiobooks in ../AudioBooks/
"""

import sys
import time
import logging
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))
from lib.audio_player import AudioPlayer

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def format_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS or MM:SS."""
    if seconds < 0:
        return "00:00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def find_audiobooks(base_path: Path) -> list[Path]:
    """Find audiobook folders (folders containing audio files)."""
    audiobooks = []
    audio_extensions = {'.mp3', '.m4a', '.m4b', '.ogg', '.flac'}

    for item in base_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Check if folder contains audio files
            has_audio = any(
                f.suffix.lower() in audio_extensions
                for f in item.iterdir() if f.is_file()
            )
            if has_audio:
                audiobooks.append(item)

    return audiobooks


def print_status(player: AudioPlayer):
    """Print current player status."""
    print("\n" + "=" * 60)
    print(f"Title: {player.title}")
    print(f"Status: {'Playing' if player.is_playing else 'Paused'}")
    print(f"File: {player.current_file_index + 1}/{player.file_count}")
    print(f"Position: {format_time(player.position)} / {format_time(player.duration)}")
    print(f"Total: {format_time(player.total_position)} / {format_time(player.total_duration)}")
    print(f"Volume: {player.volume}%")

    if player.current_chapter:
        ch = player.current_chapter
        print(f"Chapter: {ch.index + 1}/{player.chapter_count} - {ch.title}")
    print("=" * 60)


def print_help():
    """Print available commands."""
    print("""
Commands:
  p, play      - Play/resume
  s, pause     - Pause
  space        - Toggle play/pause

  f, forward   - Skip forward 30 seconds
  b, back      - Skip back 30 seconds
  ff           - Skip forward 5 minutes
  bb           - Skip back 5 minutes

  n, next      - Next chapter
  v, prev      - Previous chapter
  c, chapters  - List all chapters
  g <num>      - Go to chapter number

  +, up        - Volume up 5%
  -, down      - Volume down 5%
  vol <num>    - Set volume (0-100)

  i, info      - Show current status
  h, help      - Show this help
  q, quit      - Quit
""")


def list_chapters(player: AudioPlayer):
    """List all chapters with current marker."""
    current = player.current_chapter
    print("\nChapters:")
    print("-" * 50)
    for ch in player.chapters:
        marker = " >> " if current and ch.index == current.index else "    "
        print(f"{marker}{ch.index + 1:3}. {ch.title}")
    print("-" * 50)


def main():
    # Determine audiobook path
    if len(sys.argv) > 1:
        audiobook_path = Path(sys.argv[1])
    else:
        # Look for audiobooks in default location
        base_path = Path(__file__).parent.parent / "AudioBooks"
        if not base_path.exists():
            print(f"Error: AudioBooks folder not found at {base_path}")
            print("Usage: python test_audio.py <audiobook_path>")
            sys.exit(1)

        audiobooks = find_audiobooks(base_path)
        if not audiobooks:
            print(f"No audiobooks found in {base_path}")
            sys.exit(1)

        print("\nAvailable audiobooks:")
        for i, ab in enumerate(audiobooks):
            print(f"  {i + 1}. {ab.name}")

        if len(audiobooks) == 1:
            audiobook_path = audiobooks[0]
            print(f"\nUsing: {audiobook_path.name}")
        else:
            choice = input("\nSelect audiobook (number): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(audiobooks):
                    audiobook_path = audiobooks[idx]
                else:
                    print("Invalid selection")
                    sys.exit(1)
            except ValueError:
                print("Invalid input")
                sys.exit(1)

    # Create and load player
    print(f"\nLoading audiobook: {audiobook_path}")

    with AudioPlayer() as player:
        if not player.load_audiobook(audiobook_path):
            print("Failed to load audiobook")
            sys.exit(1)

        print(f"\nLoaded: {player.title}")
        print(f"Files: {player.file_count}")
        print(f"Chapters: {player.chapter_count}")
        print(f"Duration: {format_time(player.total_duration)}")

        print_help()
        print("\nType 'p' to start playing, 'h' for help, 'q' to quit\n")

        while True:
            try:
                cmd = input("> ").strip().lower()

                if not cmd:
                    continue

                # Playback controls
                if cmd in ('p', 'play'):
                    player.play()
                    print("Playing...")

                elif cmd in ('s', 'pause'):
                    player.pause()
                    print("Paused")

                elif cmd == 'space' or cmd == ' ':
                    player.toggle_playback()
                    print("Playing..." if player.is_playing else "Paused")

                # Seeking
                elif cmd in ('f', 'forward'):
                    player.seek(30)
                    print(f"Skipped forward 30s -> {format_time(player.position)}")

                elif cmd in ('b', 'back'):
                    player.seek(-30)
                    print(f"Skipped back 30s -> {format_time(player.position)}")

                elif cmd == 'ff':
                    player.seek(300)
                    print(f"Skipped forward 5min -> {format_time(player.position)}")

                elif cmd == 'bb':
                    player.seek(-300)
                    print(f"Skipped back 5min -> {format_time(player.position)}")

                # Chapter navigation
                elif cmd in ('n', 'next'):
                    player.next_chapter()
                    if player.current_chapter:
                        print(f"Chapter: {player.current_chapter.title}")

                elif cmd in ('v', 'prev'):
                    player.previous_chapter()
                    if player.current_chapter:
                        print(f"Chapter: {player.current_chapter.title}")

                elif cmd in ('c', 'chapters'):
                    list_chapters(player)

                elif cmd.startswith('g '):
                    try:
                        ch_num = int(cmd[2:]) - 1
                        if 0 <= ch_num < len(player.chapters):
                            ch = player.chapters[ch_num]
                            player.seek_to_position(ch.spine, ch.offset)
                            print(f"Jumped to chapter: {ch.title}")
                        else:
                            print(f"Invalid chapter number (1-{player.chapter_count})")
                    except ValueError:
                        print("Usage: g <chapter_number>")

                # Volume
                elif cmd in ('+', 'up'):
                    player.volume = player.volume + 5
                    print(f"Volume: {player.volume}%")

                elif cmd in ('-', 'down'):
                    player.volume = player.volume - 5
                    print(f"Volume: {player.volume}%")

                elif cmd.startswith('vol '):
                    try:
                        vol = int(cmd[4:])
                        player.volume = vol
                        print(f"Volume: {player.volume}%")
                    except ValueError:
                        print("Usage: vol <0-100>")

                # Info
                elif cmd in ('i', 'info'):
                    print_status(player)

                elif cmd in ('h', 'help'):
                    print_help()

                elif cmd in ('q', 'quit', 'exit'):
                    print("Goodbye!")
                    break

                else:
                    print(f"Unknown command: {cmd} (type 'h' for help)")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")


if __name__ == '__main__':
    main()

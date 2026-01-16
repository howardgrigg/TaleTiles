#!/usr/bin/env python3
"""
Integration Test for TaleTiles Player - Phase 3 Validation

Tests the complete flow:
1. Register an audiobook with a card
2. Place card to start playback
3. Play for a bit, then remove card (saves position)
4. Place card again (resumes from saved position)

Usage:
    python test_integration.py
"""

import sys
import time
import tempfile
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.audio_player import AudioPlayer
from lib.rfid_handler import RFIDHandler
from lib.state_manager import StateManager


def format_time(seconds: float) -> str:
    """Format seconds as MM:SS."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"


def test_state_manager():
    """Test StateManager functionality."""
    print("\n" + "=" * 60)
    print("Test 1: StateManager")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        config_path = f.name

    try:
        state = StateManager(config_path)

        # Test volume
        print("\n1.1 Testing volume...")
        state.volume = 80
        assert state.volume == 80, "Volume not set"
        print(f"     Volume set to {state.volume}%")

        # Test registration
        print("\n1.2 Testing audiobook registration...")
        entry = state.register_audiobook(
            card_id="test123",
            path="/tmp/fake/audiobook",
            title="Test Audiobook"
        )
        assert entry.title == "Test Audiobook", "Title not set"
        print(f"     Registered: {entry.title}")

        # Test lookup
        print("\n1.3 Testing audiobook lookup...")
        found = state.get_audiobook("test123")
        assert found is not None, "Audiobook not found"
        assert found.title == "Test Audiobook", "Title mismatch"
        print(f"     Found: {found.title}")

        # Test position update
        print("\n1.4 Testing position update...")
        state.update_playback_position("test123", file_index=2, position=145.5)
        state.save()

        # Reload and verify
        state2 = StateManager(config_path)
        found2 = state2.get_audiobook("test123")
        assert found2.current_file_index == 2, "File index not saved"
        assert found2.position_seconds == 145.5, "Position not saved"
        print(f"     Position saved: file {found2.current_file_index}, {found2.position_seconds}s")

        # Test unregister
        print("\n1.5 Testing unregister...")
        result = state2.unregister_audiobook("test123")
        assert result is True, "Unregister failed"
        assert state2.get_audiobook("test123") is None, "Still found after unregister"
        print("     Unregistered successfully")

        print("\n✓ StateManager tests passed!")

    finally:
        Path(config_path).unlink(missing_ok=True)


def test_integrated_flow():
    """Test integrated player flow with mock RFID."""
    print("\n" + "=" * 60)
    print("Test 2: Integrated Player Flow")
    print("=" * 60)

    # Find the sample audiobook
    audiobook_path = Path(__file__).parent.parent / "AudioBooks"
    audiobooks = list(audiobook_path.iterdir()) if audiobook_path.exists() else []
    audiobooks = [p for p in audiobooks if p.is_dir() and not p.name.startswith('.')]

    if not audiobooks:
        print("\n⚠ No audiobooks found, skipping integration test")
        return

    sample_audiobook = audiobooks[0]
    print(f"\nUsing audiobook: {sample_audiobook.name}")

    # Create temp config
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        config_path = f.name

    try:
        # Initialize components
        state = StateManager(config_path)
        audio = AudioPlayer()
        rfid = RFIDHandler(mock_mode=True)

        # Register the audiobook
        print("\n2.1 Registering audiobook...")
        card_id = "card_abc123"
        state.register_audiobook(card_id, sample_audiobook, "Test Book")
        print(f"     Registered with card: {card_id}")

        # Simulate card placement
        print("\n2.2 Simulating card placement...")
        entry = state.get_audiobook(card_id)
        assert entry is not None

        audio.load_audiobook(entry.path)
        audio.volume = state.volume
        audio.play()
        time.sleep(2)

        pos1 = audio.position
        print(f"     Playing at position: {format_time(pos1)}")
        assert audio.is_playing, "Should be playing"

        # Skip forward
        print("\n2.3 Skipping forward 30s...")
        audio.seek(30)
        time.sleep(0.5)
        pos2 = audio.position
        print(f"     New position: {format_time(pos2)}")
        assert pos2 > pos1, "Position should have advanced"

        # Simulate card removal (save position)
        print("\n2.4 Simulating card removal (saving position)...")
        saved_file = audio.current_file_index
        saved_pos = audio.position
        state.update_playback_position(card_id, saved_file, saved_pos)
        state.save()
        audio.stop()
        print(f"     Saved: file {saved_file}, position {format_time(saved_pos)}")

        # Reload state (simulating restart)
        print("\n2.5 Reloading state (simulating restart)...")
        state2 = StateManager(config_path)
        entry2 = state2.get_audiobook(card_id)
        print(f"     Loaded: file {entry2.current_file_index}, position {format_time(entry2.position_seconds)}")
        assert entry2.current_file_index == saved_file, "File index not restored"
        assert abs(entry2.position_seconds - saved_pos) < 1, "Position not restored"

        # Simulate card re-placement (resume)
        print("\n2.6 Simulating card re-placement (resuming)...")
        audio2 = AudioPlayer()
        audio2.load_audiobook(entry2.path)
        audio2.restore_state({
            'file_index': entry2.current_file_index,
            'position': entry2.position_seconds,
        })
        audio2.play_from_state()
        time.sleep(1)

        resumed_pos = audio2.position
        print(f"     Resumed at: {format_time(resumed_pos)}")
        assert abs(resumed_pos - saved_pos) < 5, "Resume position too far off"

        audio2.cleanup()

        print("\n✓ Integrated flow tests passed!")

    finally:
        Path(config_path).unlink(missing_ok=True)


def test_list_and_check():
    """Test list and check functionality."""
    print("\n" + "=" * 60)
    print("Test 3: List and Check Commands")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        config_path = f.name

    try:
        state = StateManager(config_path)

        # Register a few audiobooks
        state.register_audiobook("card1", "/tmp/book1", "Book One")
        state.register_audiobook("card2", "/tmp/book2", "Book Two")
        state.save()

        print("\n3.1 Listing audiobooks...")
        audiobooks = state.get_all_audiobooks()
        print(f"     Found {len(audiobooks)} audiobooks")
        for ab in audiobooks:
            print(f"     - {ab.title} ({ab.card_id})")

        print("\n3.2 Checking for missing paths...")
        missing = state.validate_paths()
        print(f"     Found {len(missing)} missing paths")
        # Both should be missing since they're fake paths
        assert len(missing) == 2, "Should detect missing paths"

        print("\n✓ List and check tests passed!")

    finally:
        Path(config_path).unlink(missing_ok=True)


def main():
    print("\n" + "=" * 60)
    print("TaleTiles Integration Tests")
    print("=" * 60)

    try:
        test_state_manager()
        test_integrated_flow()
        test_list_and_check()

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60 + "\n")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

```markdown
# Audiobook Player Project Plan

## Project Goal

Build a screen-free, RFID-controlled audiobook player for an 8-year-old child to use at bedtime. The device should be simple, intuitive, and encourage independent reading without requiring a phone or tablet.

## Core Principles

- **No backlit screens** - e-ink display only for status information
- **Physical interaction** - RFID cards and buttons provide tactile experience
- **Simple to maintain** - easy for parent to add new audiobooks over time
- **Robust** - kid-proof design with minimal points of failure
- **Position memory** - always resume where child left off

## Hardware Components

### Computing & Audio
- Raspberry Pi 3B or 3B+ (built-in 3.5mm audio jack)
- 128GB or 256GB microSD card (Class 10+)
- Power supply (5V 2.5A minimum) or USB power bank for portability
- Speaker (3.5mm connected) or headphones

### Input/Output
- RC522 RFID reader module (e.g., Jaycar XC4506)
- Pack of 10-20 RFID cards/tags
- Waveshare 2.13" e-ink display HAT (black/white)
- 5 tactile push buttons (momentary)
- Jumper wires (male-to-female)
- Breadboard (for prototyping)

### Optional
- Project enclosure/case (or 3D print custom)
- Heatsinks for Pi
- USB card reader for file transfers

### Estimated Cost
- Minimal setup: ~$120-150 NZD
- With case and better speaker: ~$180-220 NZD

## User Interaction Model

### Playing Audiobooks
1. Child places RFID card on reader
2. E-ink display shows book title and status
3. Audiobook begins playing from last saved position
4. Child uses buttons to control playback
5. Removing card pauses and saves position
6. Replacing same card resumes playback

### Physical Controls (5 Buttons)
1. **Play/Pause** - toggle playback
2. **Volume Up** - increase volume
3. **Volume Down** - decrease volume
4. **Skip Back** - single click: 30sec back | double click: previous chapter
5. **Skip Forward** - single click: 30sec forward | double click: next chapter

### E-ink Display Information
```
┌──────────────────────┐
│ Charlotte's Web      │  ← Book title (truncated if long)
│                      │
│ Ch 3/12  15m left    │  ← Chapter/time info
│                      │
│ ▶ Playing      ♪75%  │  ← Status + volume
└──────────────────────┘
```

## File Organization & Management

### Directory Structure
```
/home/pi/
├── audiobook-player/
│   ├── player.py              # Main application
│   ├── add_book.py            # Registration helper script
│   ├── config.json            # RFID mappings & playback state
│   ├── requirements.txt       # Python dependencies
│   └── lib/
│       ├── rfid_handler.py    # RFID card detection
│       ├── audio_player.py    # Audio playback wrapper
│       ├── button_handler.py  # GPIO button input
│       ├── display_manager.py # E-ink display control
│       └── state_manager.py   # Config persistence
└── audiobooks/
    ├── charlottes-web/
    │   ├── disc1/
    │   │   ├── 01.mp3
    │   │   └── 02.mp3
    │   └── disc2/
    │       └── 01.mp3
    ├── the-hobbit/
    │   └── hobbit.m4b
    └── treasure-island/
        ├── chapter-01.mp3
        └── chapter-02.mp3
```

### Supported Audiobook Formats
- **M4B files** - single file with embedded chapter markers (preferred)
- **MP3 files** - single file or multiple files (one per chapter)
- **M4A, OGG, FLAC** - supported but less common

### File Scanning Logic
- Recursively scan audiobook folder for all audio files
- Sort by full path (alphabetical) - handles disc1/disc2 structure naturally
- Build playlist from sorted file list
- Cache playlist to avoid rescanning on every card placement
- Ignore hidden files/folders (starting with `.`)

### Adding New Audiobooks - Parent Workflow

1. **Obtain audiobook files** (from library app, purchase, etc.)
2. **Copy to Pi:**
   ```bash
   scp -r "Book Name" pi@raspberrypi:/home/pi/audiobooks/
   ```
3. **Register with RFID card:**
   ```bash
   ssh pi@raspberrypi
   cd /home/pi/audiobook-player
   ./add_book.py
   ```
4. **Helper script prompts:**
   - Place RFID card on reader (detects ID)
   - Select audiobook folder from available list
   - Enter display title
   - Confirmation and registration complete

5. **Physical card preparation:**
   - Write book title on card or print label
   - Card is ready for child to use

### Helper Script Features
```bash
./add_book.py              # Interactive registration
./add_book.py --list       # Show all registered books
./add_book.py --check      # Verify paths, find issues
./add_book.py --remove     # Unregister a card
```

## Configuration & State Management

### Config File Structure (config.json)
```json
{
  "global_volume": 75,
  "audiobooks": {
    "a1b2c3d4": {
      "path": "/home/pi/audiobooks/charlottes-web",
      "title": "Charlotte's Web",
      "current_file": "disc1/chapter-03.mp3",
      "position_seconds": 145.5,
      "playlist": [
        "disc1/chapter-01.mp3",
        "disc1/chapter-02.mp3",
        "disc1/chapter-03.mp3"
      ],
      "last_played": "2026-01-15T20:30:00",
      "added_date": "2026-01-10"
    },
    "e5f6g7h8": {
      "path": "/home/pi/audiobooks/the-hobbit",
      "title": "The Hobbit",
      "current_file": "hobbit.m4b",
      "position_seconds": 3240.2,
      "playlist": ["hobbit.m4b"],
      "last_played": "2026-01-14T21:15:00",
      "added_date": "2026-01-08"
    }
  }
}
```

### State Persistence
- Save playback position every 30 seconds during playback
- Save immediately on card removal or shutdown
- Restore volume and last position on startup
- Cache playlist to avoid folder rescanning

## System Architecture

### High-Level Component Diagram
```
┌─────────────────────────────────────┐
│     Main Event Loop                 │
│  (monitors RFID + buttons)          │
└──┬──────────────┬──────────────┬────┘
   │              │              │
   ▼              ▼              ▼
┌─────────┐  ┌──────────┐  ┌──────────┐
│  RFID   │  │ Button   │  │ Display  │
│ Handler │  │ Handler  │  │ Manager  │
└────┬────┘  └────┬─────┘  └────┬─────┘
     │            │              │
     └────────────┼──────────────┘
                  ▼
         ┌────────────────┐
         │ Audio Player   │
         │   (mpv/vlc)    │
         └────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │ State Manager  │
         │ (config.json)  │
         └────────────────┘
```

### Component Responsibilities

**Main Event Loop (player.py)**
- Orchestrates all components
- Monitors RFID reader continuously
- Listens for GPIO button presses
- Updates display when state changes
- Runs as systemd service on boot

**RFID Handler (rfid_handler.py)**
- Detects card placement and removal events
- Returns card ID to main loop
- Debounces to avoid spurious reads

**Button Handler (button_handler.py)**
- Sets up GPIO interrupt handlers
- Detects single vs double clicks (300ms timeout)
- Sends commands to audio player
- Handles volume changes with immediate feedback

**Audio Player Wrapper (audio_player.py)**
- Controls mpv or vlc via Python library
- Handles M4B (with chapters) and MP3 playlists
- Supports: play, pause, seek, volume, chapter navigation
- Reports current position and metadata back
- Scans and builds playlist from audiobook folder

**Display Manager (display_manager.py)**
- Renders text and simple graphics to e-ink
- Updates on state changes (book loaded, playback status, volume)
- Batches updates to minimize e-ink flicker
- Shows error messages when needed

**State Manager (state_manager.py)**
- Reads and writes config.json
- Tracks playback position per audiobook
- Persists volume setting globally
- Validates RFID to audiobook mappings
- Handles missing files gracefully

## Technology Stack

### Software
- **OS:** Raspberry Pi OS Lite (headless, no desktop)
- **Language:** Python 3
- **Audio Backend:** mpv (recommended) or vlc
- **Auto-start:** systemd service

### Python Libraries
- `mfrc522` or `pirc522` - RFID reader interface
- `python-mpv` or `python-vlc` - audio playback control
- `gpiozero` - GPIO button handling with event detection
- `Pillow` (PIL) - image/text rendering for e-ink
- Waveshare e-ink library (display-specific)
- Standard library: `json`, `pathlib`, `logging`, `datetime`

## Implementation Behavior Details

### Double-Click Detection
- Timeout: 300ms between clicks
- Strategy: Execute single-click action immediately
- If second click detected within timeout, cancel single-click and execute double-click action
- More responsive than waiting to determine click type

### Chapter Navigation
- **For M4B files:** Use embedded chapter markers
- **For MP3 playlists:** 
  - "Next chapter" = next file in playlist
  - "Previous chapter" = previous file (or restart current if >5 seconds in)

### Error Handling
- Unknown RFID card → display "Unknown card" message on e-ink
- Missing audiobook files → display error, log issue
- Audio playback errors → log and attempt recovery
- Config corruption → backup and recreate from defaults

### Startup Behavior
- Restore global volume from config
- If RFID card is present on reader at boot, do NOT auto-play
- Wait for card removal then replacement to begin playback
- Display "Ready" message when system initialized

## Implementation Phases

### Phase 1: Basic Audio Playback
**Goal:** Validate hardware and audio output
- Install and configure Raspberry Pi OS
- Test 3.5mm audio output with test file
- Install mpv and test M4B/MP3 playback
- Verify audio quality and performance

### Phase 2: RFID Reading
**Goal:** Validate RFID hardware integration
- Wire RC522 module to GPIO pins
- Install RFID library
- Write simple script to read card IDs
- Test card detection and removal events
- Verify reliable reading

### Phase 3: Core Player Logic
**Goal:** Build functional audiobook player
- Implement AudioPlayer class (scan, playlist, playback)
- Implement StateManager class (config read/write)
- Create basic player.py that responds to RFID
- Test playback with position saving/resuming
- Handle both M4B and MP3 formats

### Phase 4: Physical Buttons
**Goal:** Add tactile playback controls
- Wire 5 buttons to GPIO
- Implement button handler with debouncing
- Add single/double-click detection
- Connect buttons to player functions
- Test volume control and seeking

### Phase 5: E-ink Display
**Goal:** Add visual feedback
- Wire e-ink display HAT to Pi
- Install Waveshare library
- Implement DisplayManager class
- Show book title, chapter, time, status
- Update display on all state changes

### Phase 6: Helper Script & Polish
**Goal:** Complete system for production use
- Build add_book.py registration script
- Add list/check/remove commands
- Create systemd service for auto-start
- Comprehensive error handling and logging
- Test complete workflow from setup to daily use
- Build/3D print enclosure
- Documentation for future maintenance

## Testing Checklist

### Hardware Validation
- [ ] Audio output quality acceptable
- [ ] RFID reads reliably within expected range
- [ ] All buttons respond correctly
- [ ] E-ink display is readable and updates properly
- [ ] Power supply provides stable operation

### Software Validation
- [ ] M4B files play with chapter navigation
- [ ] MP3 playlists play in correct order
- [ ] Subdirectory structures handled correctly
- [ ] Position saved and restored accurately
- [ ] Volume persists across reboots
- [ ] Card removal pauses immediately
- [ ] Card replacement resumes correctly
- [ ] Double-click detection works reliably
- [ ] Display shows accurate information
- [ ] Unknown cards handled gracefully
- [ ] Missing files handled gracefully

### Parent Workflow
- [ ] Adding new books is straightforward
- [ ] Helper script is intuitive
- [ ] File transfer process is documented
- [ ] Troubleshooting common issues is clear

### Child Experience
- [ ] 8-year-old can operate independently
- [ ] Buttons are responsive and intuitive
- [ ] Display provides useful feedback
- [ ] Device is enjoyable to use
- [ ] Bedtime-appropriate (no bright lights)

## Future Enhancements (Out of Scope)

- Multiple user profiles with separate progress tracking
- Sleep timer (auto-pause after X minutes)
- Bookmarks within audiobooks
- Bluetooth speaker support
- Web interface for remote management
- Statistics (listening time, books completed)
- Multi-language support
- Podcast/radio stream support

## Success Criteria

The project is successful when:
1. An 8-year-old can independently select and play audiobooks using RFID cards
2. Parent can add new audiobooks in under 5 minutes
3. Device reliably remembers playback position
4. Physical controls are intuitive and responsive
5. System runs stable for weeks without intervention
6. Child prefers this device over screen-based alternatives for bedtime listening

## Notes & Considerations

- **Audiobook Sources:** Parent responsible for obtaining audiobook files (library apps, purchases, etc.) - DRM removal is user's legal responsibility
- **Card Labeling:** Consider allowing child to decorate cards or using printed labels with cover art
- **Volume Limits:** May want to implement maximum volume cap for hearing safety
- **Power Management:** No graceful shutdown button planned - safe to unplug when paused
- **Portability:** Battery power pack option available for room-to-room use
- **Maintenance:** Anticipate needing to re-flash SD card or debug issues - keep good documentation

---

*Document Version: 1.0*  
*Last Updated: 2026-01-15*  
*Project Owner: Howard*
```

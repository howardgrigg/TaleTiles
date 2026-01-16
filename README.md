# TaleTiles Audiobook Player

A screen-free, RFID-controlled audiobook player designed for children. Place a card to play, remove to pause and save your position.

## Project Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Basic Audio Playback | Complete |
| Phase 2 | RFID Reading | Complete |
| Phase 3 | Core Player Logic | Complete |
| Phase 4 | Physical Buttons | Complete |
| Phase 5 | E-ink Display | Complete |
| Phase 6 | Polish & Deployment | Complete |

## Features Working

### Audio Playback (Phase 1)
- Load audiobooks from folders with metadata.json
- Support for MP3 files (multiple parts)
- Chapter navigation using metadata
- Play, pause, seek, volume control
- Position tracking within files

### RFID Detection (Phase 2)
- Card placement and removal detection
- Debounced readings for reliability
- Mock mode for development without hardware
- Event callbacks for card events

### Core Player Logic (Phase 3)
- RFID card to audiobook mapping
- Automatic position save on card removal
- Position restore on card placement
- Periodic position saving (every 30 seconds)
- Volume persistence across sessions
- `add_book.py` helper for registration

### Physical Buttons (Phase 4)
- 5-button support (Play/Pause, Vol+, Vol-, Skip Back, Skip Forward)
- Double-click detection for chapter navigation
- GPIO support for Raspberry Pi
- Keyboard simulation for development

### Display (Phase 5)
- **Waveshare 2.13" e-ink display** (250x122 pixels) - default option
- **16x2 Character LCD** (HD44780 compatible) - alternative option
- Shows: book title, chapter info, time remaining, playback status, volume
- Updates on state changes (play/pause, chapter, volume)
- Configurable via `config.json` - switch between display types
- Mock mode renders to console for development

### Deployment & Polish (Phase 6)
- systemd service for auto-start on boot
- Install script for easy Pi setup
- Control script (`ctl.sh`) for service management
- Comprehensive deployment documentation
- Log rotation and management

## Quick Start (Raspberry Pi)

```bash
# Copy files to Pi
scp -r audiobook-player pi@raspberrypi:~/

# SSH into Pi and install
ssh pi@raspberrypi
cd ~/audiobook-player
chmod +x install.sh
./install.sh

# Register audiobooks
./ctl.sh add

# Start the player
./ctl.sh start
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete setup instructions.

## Hardware Requirements

- Raspberry Pi 3B/3B+ (or newer)
- RC522 RFID reader module
- RFID cards/tags
- 5 tactile push buttons
- Speaker (3.5mm) or headphones
- Display (choose one):
  - **Option A:** Waveshare 2.13" V4 e-ink display (default)
  - **Option B:** 16x2 Character LCD (HD44780 compatible, 4-bit mode)

See [WIRING.md](WIRING.md) for detailed wiring instructions.

## Software Requirements

- Python 3.10+
- mpv media player
- python-mpv library

## Installation

### On Development Machine (macOS/Linux)

```bash
cd audiobook-player

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install mpv (macOS)
brew install mpv
```

### On Raspberry Pi

```bash
cd audiobook-player

# Install system dependencies
sudo apt-get update
sudo apt-get install mpv python3-pip python3-venv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements-pi.txt

# Enable SPI for RFID
sudo raspi-config  # Interface Options → SPI → Enable
sudo reboot
```

## Usage

### Register an Audiobook

```bash
source venv/bin/activate

# Interactive registration
python add_book.py --mock          # Development (keyboard input)
python add_book.py                  # Raspberry Pi (real RFID)

# Other commands
python add_book.py --list          # List registered books
python add_book.py --check         # Check for missing paths
python add_book.py --remove        # Remove a registration
```

### Run the Player

```bash
source venv/bin/activate

# Development mode (keyboard controls)
python player.py --mock

# Production mode (real hardware)
python player.py
```

### Mock Mode Controls

| Key | Action |
|-----|--------|
| `1-5` | Simulate RFID card 1-5 |
| `r` | Remove current card |
| `Space` | Play/Pause |
| `+` / `=` | Volume Up |
| `-` | Volume Down |
| `,` | Skip Back 30s (double-tap: previous chapter) |
| `.` | Skip Forward 30s (double-tap: next chapter) |
| `i` | Show current info |
| `h` | Show help |
| `Ctrl+C` | Quit |

### Button Functions (Hardware)

| Button | Single Press | Double Press |
|--------|--------------|--------------|
| Play/Pause | Toggle playback | - |
| Volume Up | +5% volume | - |
| Volume Down | -5% volume | - |
| Skip Back | 30 seconds back | Previous chapter |
| Skip Forward | 30 seconds forward | Next chapter |

## Audiobook Format

Audiobooks should be organized in folders with the following structure:

```
AudioBooks/
└── Book Name/
    ├── metadata/
    │   ├── metadata.json    # Book info and chapter markers
    │   └── cover.jpg        # Cover image (optional)
    ├── Part 001.mp3
    ├── Part 002.mp3
    └── ...
```

### metadata.json Format

```json
{
  "title": "Book Title",
  "creator": [
    {"name": "Author Name", "role": "author"},
    {"name": "Narrator Name", "role": "narrator"}
  ],
  "spine": [
    {"duration": 3600.0, "type": "audio/mpeg", "bitrate": 64}
  ],
  "chapters": [
    {"title": "Chapter 1", "spine": 0, "offset": 0},
    {"title": "Chapter 2", "spine": 0, "offset": 300}
  ]
}
```

## Project Structure

```
audiobook-player/
├── player.py              # Main application
├── add_book.py            # Audiobook registration helper
├── ctl.sh                 # Control script (start/stop/status)
├── install.sh             # Installation script for Pi
├── config.json            # Runtime configuration (auto-created)
├── requirements.txt       # Development dependencies
├── requirements-pi.txt    # Raspberry Pi dependencies
├── taletiles.service      # systemd service file
├── logging_config.py      # Logging configuration
├── WIRING.md              # Hardware wiring guide
├── DEPLOYMENT.md          # Deployment guide
├── README.md              # This file
├── lib/
│   ├── audio_player.py    # Audio playback (mpv wrapper)
│   ├── rfid_handler.py    # RFID card detection
│   ├── button_handler.py  # GPIO button handling
│   ├── display_manager.py # Display control (e-ink or LCD)
│   └── state_manager.py   # Configuration persistence
└── test_*.py              # Test scripts
```

## Testing

```bash
source venv/bin/activate

# Test audio playback
python test_audio.py

# Test RFID handler
python test_rfid.py

# Test button handler
python test_buttons.py

# Test full integration
python test_integration.py
```

## Configuration

Configuration is stored in `config.json`:

```json
{
  "global_volume": 75,
  "display": {
    "type": "eink",
    "lcd_rs": 16,
    "lcd_e": 18,
    "lcd_d4": 20,
    "lcd_d5": 21,
    "lcd_d6": 22,
    "lcd_d7": 23
  },
  "audiobooks": {
    "card_id": {
      "path": "/path/to/audiobook",
      "title": "Book Title",
      "current_file_index": 0,
      "position_seconds": 123.4,
      "last_played": "2024-01-15T20:30:00",
      "added_date": "2024-01-10"
    }
  }
}
```

### Display Options

| Setting | Description |
|---------|-------------|
| `type` | `"eink"` (Waveshare 2.13") or `"lcd1602"` (16x2 Character LCD) |
| `lcd_rs` | LCD Register Select pin (GPIO, BCM numbering) |
| `lcd_e` | LCD Enable pin |
| `lcd_d4`-`lcd_d7` | LCD data pins (4-bit mode) |

To switch to LCD display, change `"type": "eink"` to `"type": "lcd1602"`.

## Troubleshooting

### Audio not playing
- Check mpv is installed: `mpv --version`
- Check audio output: `mpv /path/to/test.mp3`
- Verify volume is not muted

### RFID not detecting
- Verify SPI is enabled: `ls /dev/spi*`
- Check wiring connections
- Try `python test_rfid.py --real`

### Buttons not responding
- Check GPIO wiring
- Verify pull-up resistors are enabled
- Try `python test_buttons.py`

### E-ink display not working
- Check SPI is enabled: `ls /dev/spi*`
- Verify Waveshare library is installed
- Check wiring matches WIRING.md
- E-ink updates are slow (~2 seconds) - this is normal

### LCD display not working
- Verify RPLCD is installed: `pip show RPLCD`
- Check `config.json` has `"type": "lcd1602"`
- Verify GPIO wiring matches config pins
- Adjust contrast potentiometer (V0 pin)
- Check 5V power to LCD VDD pin

## License

This project is for personal use.

---

*Last updated: Phase 6 Complete - All phases finished!*

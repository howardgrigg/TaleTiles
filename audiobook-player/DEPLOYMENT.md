# TaleTiles Deployment Guide

Complete guide for deploying TaleTiles to a Raspberry Pi.

## Prerequisites

### Hardware
- Raspberry Pi 3B/3B+ or newer
- 16GB+ microSD card (Class 10 recommended)
- RC522 RFID reader module
- RFID cards/tags (one per audiobook)
- 5 tactile push buttons
- Waveshare 2.13" V4 e-ink display
- Speaker with 3.5mm jack or USB speaker
- 5V 2.5A+ power supply

### Software
- Raspberry Pi OS Lite (64-bit recommended)
- SSH access configured

## Step 1: Prepare the Raspberry Pi

### Flash Raspberry Pi OS

1. Download Raspberry Pi Imager
2. Select "Raspberry Pi OS Lite (64-bit)"
3. Click the gear icon to configure:
   - Set hostname: `taletiles`
   - Enable SSH with password authentication
   - Set username: `pi` and password
   - Configure WiFi (optional)
4. Flash to SD card

### First Boot

```bash
# SSH into the Pi
ssh pi@taletiles.local

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Set timezone
sudo raspi-config  # Localisation Options → Timezone

# Enable SPI (for RFID and display)
sudo raspi-config  # Interface Options → SPI → Enable

# Reboot
sudo reboot
```

## Step 2: Wire the Hardware

Follow [WIRING.md](WIRING.md) to connect:

1. **RC522 RFID Reader** (SPI)
2. **5 Buttons** (GPIO with pull-ups)
3. **E-ink Display** (SPI, shared with RFID)
4. **Speaker** (3.5mm audio jack)

### Verify Wiring

```bash
# Check SPI is enabled
ls /dev/spi*
# Should show: /dev/spidev0.0  /dev/spidev0.1

# Check GPIO access
gpio readall  # (if wiringpi installed)
```

## Step 3: Transfer Files

From your development machine:

```bash
# Copy the audiobook-player folder to the Pi
scp -r audiobook-player pi@taletiles.local:~/

# Copy audiobooks
scp -r "AudioBooks/My Audiobook" pi@taletiles.local:~/audiobooks/
```

## Step 4: Install TaleTiles

SSH into the Pi and run:

```bash
cd ~/audiobook-player
chmod +x install.sh
./install.sh
```

This will:
- Install system dependencies (mpv, python3, etc.)
- Enable SPI if needed
- Create Python virtual environment
- Install Python packages
- Install Waveshare e-Paper library
- Create audiobooks directory
- Install and enable systemd service

**Reboot if prompted** (if SPI was just enabled).

## Step 5: Register Audiobooks

```bash
cd ~/audiobook-player
source venv/bin/activate

# Register an audiobook with an RFID card
python add_book.py

# Follow prompts:
# 1. Select audiobook from list
# 2. Enter display title
# 3. Place RFID card on reader
```

Repeat for each audiobook/card pair.

### Verify Registration

```bash
python add_book.py --list
python add_book.py --check
```

## Step 6: Test the Player

### Manual Test (Foreground)

```bash
cd ~/audiobook-player
./ctl.sh test
```

- Place an RFID card → should start playing
- Remove card → should pause and save position
- Test buttons (Play/Pause, Volume, Skip)
- Check display updates

Press `Ctrl+C` to stop.

### Service Test

```bash
# Start the service
./ctl.sh start

# Check status
./ctl.sh status

# View logs
./ctl.sh logs
```

## Step 7: Configure Auto-Start

The systemd service is already enabled during installation. TaleTiles will start automatically on boot.

```bash
# Verify service is enabled
sudo systemctl is-enabled taletiles
# Should output: enabled

# Reboot to test auto-start
sudo reboot
```

After reboot, the player should start automatically.

## Managing TaleTiles

### Control Commands

```bash
cd ~/audiobook-player

./ctl.sh start     # Start the service
./ctl.sh stop      # Stop the service
./ctl.sh restart   # Restart the service
./ctl.sh status    # Show status
./ctl.sh logs      # Follow logs (Ctrl+C to exit)
./ctl.sh test      # Run in foreground (for debugging)

./ctl.sh add       # Register new audiobook
./ctl.sh list      # List registered audiobooks
./ctl.sh check     # Check for issues
```

### Adding New Audiobooks

1. Copy audiobook to Pi:
   ```bash
   scp -r "New Audiobook" pi@taletiles.local:~/audiobooks/
   ```

2. Register with RFID card:
   ```bash
   ssh pi@taletiles.local
   cd ~/audiobook-player
   ./ctl.sh add
   ```

3. No restart required - the player will detect the new audiobook.

### Viewing Logs

```bash
# Live logs
./ctl.sh logs

# Last 100 lines
journalctl -u taletiles -n 100

# Logs from today
journalctl -u taletiles --since today
```

## Troubleshooting

### Player won't start

```bash
# Check status
./ctl.sh status

# Check logs for errors
journalctl -u taletiles -n 50

# Try running manually
./ctl.sh test
```

### No audio

```bash
# Test audio output
speaker-test -t wav -c 2

# Check audio device
aplay -l

# Force 3.5mm output
sudo raspi-config  # System Options → Audio → Headphones
```

### RFID not reading

```bash
# Check SPI
ls /dev/spi*

# Check connections (see WIRING.md)

# Test RFID
cd ~/audiobook-player
source venv/bin/activate
python test_rfid.py
```

### Display not updating

```bash
# Check SPI is enabled
ls /dev/spi*

# Check wiring (see WIRING.md)

# Test display
cd ~/audiobook-player
source venv/bin/activate
python -c "from lib.display_manager import DisplayManager; d = DisplayManager(); d.show_ready()"
```

### Buttons not working

```bash
# Test buttons
cd ~/audiobook-player
source venv/bin/activate
python test_buttons.py
```

## Backup and Restore

### Backup Configuration

```bash
# Backup config and audiobook registrations
scp pi@taletiles.local:~/audiobook-player/config.json ./taletiles-backup.json
```

### Restore Configuration

```bash
# Restore config
scp taletiles-backup.json pi@taletiles.local:~/audiobook-player/config.json
./ctl.sh restart
```

## Updating TaleTiles

```bash
cd ~/audiobook-player

# Stop service
./ctl.sh stop

# Backup config
cp config.json config.json.backup

# Update files (from development machine)
# scp -r audiobook-player/* pi@taletiles.local:~/audiobook-player/

# Restore config if needed
# cp config.json.backup config.json

# Restart
./ctl.sh start
```

## Hardware Enclosure

Consider 3D printing or building an enclosure with:
- Cutout for RFID reader (cards placed on top)
- 5 button holes on front/top
- Display window for e-ink
- Speaker grille
- Power cable access
- Ventilation holes

The enclosure should be:
- Kid-proof (no sharp edges, robust)
- Easy for a child to operate
- Stable when placing/removing cards

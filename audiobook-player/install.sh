#!/bin/bash
#
# TaleTiles Audiobook Player - Installation Script
#
# Run this script on a Raspberry Pi to install and configure TaleTiles.
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║           TaleTiles Audiobook Player Installer           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please do not run as root. Run as the 'pi' user.${NC}"
    exit 1
fi

# Check if on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi.${NC}"
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

INSTALL_DIR="$HOME/audiobook-player"
AUDIOBOOKS_DIR="$HOME/audiobooks"

echo -e "${GREEN}[1/8]${NC} Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    mpv \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-pil \
    python3-numpy \
    git

echo -e "${GREEN}[2/8]${NC} Enabling SPI interface..."
if ! grep -q "^dtparam=spi=on" /boot/config.txt 2>/dev/null && \
   ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt 2>/dev/null; then
    echo -e "${YELLOW}SPI not enabled. Enabling now...${NC}"
    if [ -f /boot/firmware/config.txt ]; then
        sudo bash -c 'echo "dtparam=spi=on" >> /boot/firmware/config.txt'
    else
        sudo bash -c 'echo "dtparam=spi=on" >> /boot/config.txt'
    fi
    SPI_ENABLED=1
else
    echo "SPI already enabled."
fi

echo -e "${GREEN}[3/8]${NC} Setting up Python virtual environment..."
cd "$INSTALL_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo -e "${GREEN}[4/8]${NC} Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements-pi.txt

# Ask about display type
echo ""
echo -e "${YELLOW}Which display are you using?${NC}"
echo "  1) Waveshare 2.13\" e-ink display (default)"
echo "  2) 16x2 Character LCD (HD44780)"
echo ""
read -p "Enter choice [1/2]: " -n 1 -r DISPLAY_CHOICE
echo ""

if [[ $DISPLAY_CHOICE == "2" ]]; then
    echo -e "${GREEN}[5/8]${NC} Configuring for LCD display..."
    # RPLCD is already in requirements-pi.txt
    # Create initial config with LCD settings
    if [ ! -f "$INSTALL_DIR/config.json" ]; then
        cat > "$INSTALL_DIR/config.json" << 'EOF'
{
  "global_volume": 75,
  "display": {
    "type": "lcd1602",
    "lcd_rs": 16,
    "lcd_e": 18,
    "lcd_d4": 20,
    "lcd_d5": 21,
    "lcd_d6": 22,
    "lcd_d7": 23
  },
  "audiobooks": {}
}
EOF
        echo "Created config.json with LCD display settings"
    else
        echo -e "${YELLOW}config.json already exists. Update 'display.type' to 'lcd1602' manually if needed.${NC}"
    fi
else
    # Install Waveshare e-Paper library
    echo -e "${GREEN}[5/8]${NC} Installing Waveshare e-Paper library..."
    if [ ! -d "$HOME/e-Paper" ]; then
        cd "$HOME"
        git clone https://github.com/waveshare/e-Paper.git
    fi
    cd "$HOME/e-Paper/RaspberryPi_JetsonNano/python"
    pip install .
    cd "$INSTALL_DIR"
fi

echo -e "${GREEN}[6/8]${NC} Creating audiobooks directory..."
mkdir -p "$AUDIOBOOKS_DIR"

echo -e "${GREEN}[7/8]${NC} Installing systemd service..."
sudo cp taletiles.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable taletiles.service

echo -e "${GREEN}[8/8]${NC} Verifying installation..."
source "$INSTALL_DIR/venv/bin/activate"
python -c "from lib.display_manager import DisplayManager; print('Display manager OK')" 2>/dev/null && echo "Display module verified" || echo -e "${YELLOW}Display module check skipped${NC}"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Installation Complete!                       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

if [[ $DISPLAY_CHOICE == "2" ]]; then
    echo -e "${YELLOW}LCD Display Selected${NC}"
    echo "Wire your 16x2 LCD as shown in WIRING.md"
    echo "Default pins: RS=GPIO16, E=GPIO18, D4-D7=GPIO20-23"
    echo ""
fi

echo "Next steps:"
echo ""
echo "  1. Copy audiobooks to: $AUDIOBOOKS_DIR"
echo "     Example: scp -r 'My Audiobook' pi@raspberrypi:~/audiobooks/"
echo ""
echo "  2. Register audiobooks with RFID cards:"
echo "     cd $INSTALL_DIR"
echo "     source venv/bin/activate"
echo "     python add_book.py"
echo ""
echo "  3. Start the player:"
echo "     sudo systemctl start taletiles"
echo ""
echo "  4. Check status:"
echo "     sudo systemctl status taletiles"
echo "     journalctl -u taletiles -f"
echo ""

if [ -n "$SPI_ENABLED" ]; then
    echo -e "${YELLOW}NOTE: SPI was just enabled. Please reboot before starting:${NC}"
    echo "     sudo reboot"
    echo ""
fi

echo "For manual testing (without systemd):"
echo "     cd $INSTALL_DIR && source venv/bin/activate"
echo "     python player.py"
echo ""

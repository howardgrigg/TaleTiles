# TaleTiles Hardware Wiring Guide

## Complete Pin Reference

All connections for TaleTiles in one table, sorted by Pi pin number:

| Pi Pin | Pi GPIO | Component | Wire | Function |
|--------|---------|-----------|------|----------|
| 1 | 3.3V | RFID + Display | Red | Power (3.3V) |
| 6 | GND | RFID + Display | Black | Ground |
| 11 | GPIO17 | E-ink Display | RST | Display reset |
| 13 | GPIO27 | RFID | RST | RFID reset |
| 18 | GPIO24 | E-ink Display | BUSY | Display busy signal |
| 19 | GPIO10 | RFID + Display | MOSI/DIN | SPI data out (shared) |
| 21 | GPIO9 | RFID | MISO | SPI data in |
| 22 | GPIO25 | E-ink Display | DC | Display data/command |
| 23 | GPIO11 | RFID + Display | SCK/CLK | SPI clock (shared) |
| 24 | GPIO8 | RFID + Display | SDA/CS | SPI chip select (shared) |
| 29 | GPIO5 | Button | Play/Pause | Toggle playback |
| 31 | GPIO6 | Button | Vol Up | Volume +5% |
| 32 | GPIO12 | Button | Vol Down | Volume -5% |
| 33 | GPIO13 | Button | Skip Back | 30s back / prev chapter |
| 34 | GND | Buttons | Black | Button common ground |
| 35 | GPIO19 | Button | Skip Fwd | 30s fwd / next chapter |

### Visual Pin Layout

```
                    Raspberry Pi GPIO Header
                    (pin 1 at top left)

        3.3V [1]  ●──────────────────●  [2]  5V
  RFID+Disp GND   [3]  ●              ●  [4]  5V
             -    [5]  ●              ●  [6]  ●  GND ──── RFID+Disp
             -    [7]  ●              ●  [8]  -
             -    [9]  ●              ●  [10] -
 Display RST      [11] ●──────────────●  [12] -
    RFID RST      [13] ●──────────────●  [14] -
             -    [15] ●              ●  [16] -
             -    [17] ●              ●  [18] ●  Display BUSY
    SPI MOSI      [19] ●──────────────●  [20] -
    SPI MISO      [21] ●──────────────●  [22] ●  Display DC
    SPI SCLK      [23] ●──────────────●  [24] ●  SPI CS (CE0)
             -    [25] ●              ●  [26] -
             -    [27] ●              ●  [28] -
  Play/Pause      [29] ●──────────────●  [30] -
      Vol Up      [31] ●──────────────●  [32] ●  Vol Down
   Skip Back      [33] ●──────────────●  [34] ●  Button GND
    Skip Fwd      [35] ●──────────────●  [36] -
             -    [37] ●              ●  [38] -
             -    [39] ●              ●  [40] -
```

---

## RC522 RFID Module

The RC522 module uses SPI to communicate with the Pi.

### Pin Connections

| RC522 Pin | Pi Pin | Pi GPIO | Description |
|-----------|--------|---------|-------------|
| SDA       | 24     | GPIO8 (CE0) | SPI Chip Select |
| SCK       | 23     | GPIO11 (SCLK) | SPI Clock |
| MOSI      | 19     | GPIO10 (MOSI) | SPI Data Out |
| MISO      | 21     | GPIO9 (MISO) | SPI Data In |
| IRQ       | -      | -       | Not used |
| GND       | 6      | GND     | Ground |
| RST       | 13     | GPIO27  | Reset |
| 3.3V      | 1      | 3.3V    | Power |

### Wiring Diagram

```
RC522 Module                 Raspberry Pi 3B/3B+
┌──────────────┐            ┌─────────────────────┐
│              │            │  Pin 1 (3.3V) ●─────┼── 3.3V
│   ┌──────┐   │            │  Pin 6 (GND)  ●─────┼── GND
│   │ RFID │   │            │  Pin 13 (GPIO27)●───┼── RST
│   │ Chip │   │            │  Pin 19 (MOSI)●─────┼── MOSI
│   └──────┘   │            │  Pin 21 (MISO)●─────┼── MISO
│              │            │  Pin 23 (SCLK)●─────┼── SCK
│  SDA SCK MOSI│            │  Pin 24 (CE0) ●─────┼── SDA
│  MISO IRQ GND│            │                     │
│  RST 3.3V    │            └─────────────────────┘
└──────────────┘
```

**Note:** The RFID RST pin uses GPIO27 to avoid conflict with the e-ink display.

### Enable SPI on Raspberry Pi

1. Run `sudo raspi-config`
2. Navigate to: Interface Options → SPI → Enable
3. Reboot: `sudo reboot`

### Verify SPI is Enabled

```bash
ls /dev/spi*
# Should show: /dev/spidev0.0  /dev/spidev0.1
```

### Install Dependencies (on Pi)

```bash
sudo apt-get update
sudo apt-get install python3-dev python3-pip
pip3 install spidev mfrc522
```

## Button Wiring (Phase 4)

Five tactile push buttons connected with internal pull-up resistors (active low).

| Button | Pi Pin | Pi GPIO | Function |
|--------|--------|---------|----------|
| Play/Pause | 29 | GPIO5 | Toggle playback |
| Volume Up | 31 | GPIO6 | Increase volume (+5%) |
| Volume Down | 32 | GPIO12 | Decrease volume (-5%) |
| Skip Back | 33 | GPIO13 | Single: 30s back / Double: prev chapter |
| Skip Forward | 35 | GPIO19 | Single: 30s forward / Double: next chapter |
| Common GND | 34 | GND | All buttons share ground |

### Button Behavior

- **Single press**: Action happens immediately
- **Double press** (Skip buttons only): Press twice within 300ms
  - First press executes single action immediately
  - Second press cancels and executes double action

### Button Wiring Diagram

```
                    ┌─────────────────────────────────────┐
                    │         Raspberry Pi GPIO           │
                    │                                     │
  ┌─────────┐       │  Pin 29 (GPIO5)  ●────── Play/Pause │
  │         │       │  Pin 31 (GPIO6)  ●────── Vol Up     │
  │ Buttons │       │  Pin 32 (GPIO12) ●────── Vol Down   │
  │         │       │  Pin 33 (GPIO13) ●────── Skip Back  │
  │  (all)  │       │  Pin 35 (GPIO19) ●────── Skip Fwd   │
  │         │       │                                     │
  │   GND ──────────│  Pin 34 (GND)    ●────── Common GND │
  └─────────┘       │                                     │
                    └─────────────────────────────────────┘

Each button connection:

Pi GPIO Pin ────┬──── [Button] ──── Pi GND (Pin 34)
                │
           (internal pull-up enabled in software)
           (button press = LOW signal)
```

### Recommended Buttons

- Tactile push buttons (momentary, normally open)
- 6mm x 6mm or 12mm x 12mm size
- Through-hole for breadboard prototyping
- Example: Generic tactile switch or arcade-style buttons for the enclosure

## E-ink Display (Phase 5)

Waveshare 2.13" V4 e-ink display (250x122 pixels, black/white).

### Pin Connections

| Display Pin | Pi Pin | Pi GPIO | Description |
|-------------|--------|---------|-------------|
| VCC         | 1      | 3.3V    | Power |
| GND         | 6      | GND     | Ground |
| DIN         | 19     | GPIO10 (MOSI) | SPI Data (shared with RFID) |
| CLK         | 23     | GPIO11 (SCLK) | SPI Clock (shared with RFID) |
| CS          | 24     | GPIO8 (CE0)   | SPI Chip Select (shared with RFID) |
| DC          | 22     | GPIO25  | Data/Command |
| RST         | 11     | GPIO17  | Reset |
| BUSY        | 18     | GPIO24  | Busy status |

### Display Layout

```
┌────────────────────────────────────────┐
│ The Wild Ones / Moonlight Brigade      │  ← Title (large font)
│                                        │
│ Ch 5/59  |  4h 32m left               │  ← Chapter / time remaining
│ Chapter 5                              │  ← Current chapter title
│────────────────────────────────────────│
│ ▶ Playing                    Vol 75%   │  ← Status bar
└────────────────────────────────────────┘
```

### SPI Sharing Note

The e-ink display and RFID reader share the SPI bus (MOSI, SCLK, CS). This works
because they use the same chip select (CE0). The display and RFID are not accessed
simultaneously - the display only updates when playback state changes.

### Install Waveshare Library (on Pi)

```bash
# Install dependencies
sudo apt-get install python3-pip python3-pil python3-numpy

# Clone Waveshare library
git clone https://github.com/waveshare/e-Paper.git
cd e-Paper/RaspberryPi_JetsonNano/python
pip3 install .
```

### Troubleshooting

- **Display not updating**: Check SPI is enabled and wiring is correct
- **Garbled display**: Verify you're using the correct driver (epd2in13_V4)
- **Slow updates**: E-ink refreshes take ~2 seconds; this is normal

---

## 16x2 Character LCD (Alternative Display)

As an alternative to the e-ink display, you can use a standard 16x2 HD44780-compatible LCD module in 4-bit mode. This is a cheaper option if you have one available.

### Pin Connections (Default)

| LCD Pin | Pi Pin | Pi GPIO | Description |
|---------|--------|---------|-------------|
| VSS     | 6      | GND     | Ground |
| VDD     | 2      | 5V      | Power (5V) |
| V0      | -      | -       | Contrast (connect to potentiometer) |
| RS      | 36     | GPIO16  | Register Select |
| RW      | 6      | GND     | Read/Write (tie to GND for write-only) |
| E       | 12     | GPIO18  | Enable |
| D0-D3   | -      | -       | Not used (4-bit mode) |
| D4      | 38     | GPIO20  | Data bit 4 |
| D5      | 40     | GPIO21  | Data bit 5 |
| D6      | 15     | GPIO22  | Data bit 6 |
| D7      | 16     | GPIO23  | Data bit 7 |
| A       | 2      | 5V      | Backlight anode (5V) |
| K       | 6      | GND     | Backlight cathode (GND) |

### LCD Wiring Diagram

```
16x2 LCD Module                 Raspberry Pi 3B/3B+
┌────────────────────┐         ┌─────────────────────┐
│  1  2  3  4  5  6  │         │                     │
│ VSS VDD V0 RS RW E │         │  Pin 2 (5V)    ●────┼── VDD, A (backlight)
│  │  │  │  │  │  │  │         │  Pin 6 (GND)   ●────┼── VSS, RW, K (backlight)
│  │  │  │  │  │  │  │         │  Pin 12 (GPIO18)●───┼── E
│  │  │  │  │  │  │  │         │  Pin 15 (GPIO22)●───┼── D6
│  7  8  9 10 11 12  │         │  Pin 16 (GPIO23)●───┼── D7
│ D0 D1 D2 D3 D4 D5  │         │  Pin 36 (GPIO16)●───┼── RS
│        │  │  │  │  │         │  Pin 38 (GPIO20)●───┼── D4
│       NC NC │  │  │          │  Pin 40 (GPIO21)●───┼── D5
│             │  │  │          │                     │
│ 13 14 15 16 │  │  │          └─────────────────────┘
│ D6 D7 A  K  │  │  │
│  │  │  │  │  │  │  │
└──┼──┼──┼──┼──┼──┼──┘
   │  │  │  │  │  │
  To Pi pins as shown above

Contrast Circuit:
                    ┌─── VDD (5V)
                    │
                   [█] 10K Potentiometer
                    │
V0 (LCD pin 3) ────┤
                    │
                   GND
```

### LCD Display Layout

```
┌────────────────┐
│>Harry Potter   │  ← Line 1: Status icon + title (truncated)
│C5/12 V75 -2h3m│  ← Line 2: Chapter, volume, time remaining
└────────────────┘
```

Status icons on LCD:
- `>` = Playing
- `=` = Paused
- `*` = Loading
- ` ` (space) = Stopped

### Configuration

To use the LCD instead of e-ink, edit `config.json`:

```json
{
  "display": {
    "type": "lcd1602",
    "lcd_rs": 16,
    "lcd_e": 18,
    "lcd_d4": 20,
    "lcd_d5": 21,
    "lcd_d6": 22,
    "lcd_d7": 23
  }
}
```

You can change the GPIO pins if needed - just update both the wiring and the config.

### Install LCD Library

```bash
source venv/bin/activate
pip install RPLCD
```

### Troubleshooting

- **Blank display**: Adjust the contrast potentiometer (V0)
- **No backlight**: Check A and K pins are connected to 5V and GND
- **Garbled characters**: Verify data pins D4-D7 are correctly wired
- **Nothing happens**: Check RPLCD is installed and `config.json` has `"type": "lcd1602"`

### Choosing Between Displays

| Feature | E-ink (Waveshare 2.13") | LCD 1602 |
|---------|-------------------------|----------|
| Resolution | 250x122 pixels | 16x2 characters |
| Update speed | ~2 seconds | Instant |
| Power usage | Very low (no backlight) | Higher (backlight) |
| Visibility | Excellent in sunlight | Needs backlight in dark |
| Cost | ~$15-20 | ~$3-5 |
| Wiring | Uses SPI (shared with RFID) | 6 GPIO pins |
| Information shown | Full title, chapter name | Abbreviated info |

# CoolLedDiy

A Python desktop application to control CoolLed LED matrix panels via Bluetooth Low Energy (BLE). Send text, images, and animations to your LED panel directly from your PC.

## Features

- **BLE Device Scanning** — Discover nearby CoolLed LED matrix panels
- **Connect & Control** — Pair with your panel and manage the connection
- **Send Text** — Render and transmit text messages to the display
- **Send Images** — Convert and send images to the LED matrix
- **Brightness / Speed / Mode Controls** — Adjust display settings in real time
- **Debug Panel** — Inspect raw BLE communication for troubleshooting and development

## Supported Devices

CoolLED, CoolLEDX, CoolLEDM, CoolLEDU, CoolLEDUX, CoolLEDUD and related variants.

## Supported Panel Sizes

12x48, 16x48, 16x64, 16x96, 32x32, 32x128 and other compatible matrix configurations.

## Tech Stack

- **Python 3.13**
- **PySide6** — Qt-based GUI
- **bleak** — Bluetooth Low Energy communication
- **Pillow** — Image processing and conversion
- **qasync** — Async event loop integration for Qt

## Setup

Requires [uv](https://docs.astral.sh/uv/) as package manager.

```bash
# Install dependencies
uv sync

# Run the application
uv run python main.py
```

## Tests

```bash
uv run pytest
```

## Screenshots

*Coming soon.*

## License

*TBD*

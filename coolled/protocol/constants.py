"""
Konstanten für das CoolLed BLE-Protokoll.

Basiert auf der Decompilation von DeviceManager.java und Light1248Utils.java.
"""

# BLE Service und Characteristic UUIDs
UUID_SERVICE = "0000fff0-0000-1000-8000-00805f9b34fb"
UUID_CHARACTERISTIC = "0000fff1-0000-1000-8000-00805f9b34fb"

# Bekannte CoolLed Gerätenamen für BLE-Scan-Filterung
DEVICE_NAMES = [
    "CoolLED", "CoolLED536", "CoolLEDX", "CoolLEDA",
    "CoolLEDS", "CoolLEDM", "CoolLEDU", "iLedBike",
    "CoolLEDUX", "iLedClock", "iDevilEyes", "iLedHat",
    "iLedHatC", "iLedOpen",
]

# BLE Verbindungsparameter (aus DeviceManager.java)
BLE_MTU_MAX_SIZE = 247
BLE_MTU_MIN_SIZE = 23
BLE_WRITE_CHAR_MAX_SIZE = 180  # Chunk-Size bei MTU 247
BLE_WRITE_CHAR_MIN_SIZE = 20   # Fallback Chunk-Size bei MTU 23
PACKET_DELAY_MS = 15           # Delay zwischen BLE-Chunks in ms

# Frame-Marker (aus Light1248Utils.java)
FRAME_START = 0x01
FRAME_END = 0x03
ESCAPE_BYTE = 0x02
ESCAPE_XOR = 0x04

# Kommando-Bytes (aus Light1248Utils.java Prefix-Listen)
CMD_MUSIC = 0x01         # musicStartString
CMD_TEXT = 0x02          # textStartString
CMD_DRAW = 0x03          # drawStartString
CMD_ANIMATION = 0x04     # animationStartString (getSendDataWithTypeStrings("04",...))
CMD_ICON = 0x05          # iconStartString
CMD_MODE = 0x06          # modeStartString
CMD_SPEED = 0x07         # speedStartString
CMD_BRIGHTNESS = 0x08    # brightStartString
CMD_SWITCH = 0x09        # switchStartString (Light1248) / SYNC_TIME (UX-Geräte)
CMD_BEGIN_TRANSFER = 0x0A  # beginTransferStartString
CMD_MIRROR = 0x0C        # getSetMirror() in CoolledUXUtils.java:3958
CMD_DEVICE_INFO = 0x1F   # getDeviceInfo() in CoolledUXUtils.java:3934

# Hinweis: CMD_SWITCH (0x09) wird auf Light1248-Geräten als Switch verwendet,
# auf CoolLEDUX-Geräten als Time-Sync (getSynchronizeTime).
# CoolLEDM/UX verwenden 0x05 für Switch.
CMD_SYNC_TIME = 0x09     # getSynchronizeTime() in CoolledUXUtils.java:4036

# Kommando-Namen für Debug-Anzeige (Dissector)
CMD_NAMES = {
    CMD_MUSIC: "MUSIC",
    CMD_TEXT: "TEXT",
    CMD_DRAW: "DRAW",
    CMD_ANIMATION: "ANIMATION",
    CMD_ICON: "ICON",
    CMD_MODE: "MODE",
    CMD_SPEED: "SPEED",
    CMD_BRIGHTNESS: "BRIGHTNESS",
    CMD_SWITCH: "SWITCH/SYNC_TIME",
    CMD_BEGIN_TRANSFER: "BEGIN_TRANSFER",
    CMD_MIRROR: "MIRROR",
    CMD_DEVICE_INFO: "DEVICE_INFO",
}

# Farb-Typen aus Scan-Record (DeviceManager.java)
COLOR_SINGLE = 0         # Einfarbig
COLOR_SEVEN = 1          # 7-Farben
COLOR_COLORFUL = 2       # Bunt
COLOR_UX = 3             # UX-Serie
COLOR_CLOCK = 4          # iLedClock

# Scan Record Byte-Positionen (aus BleDeviceSimulator.java)
SCAN_RECORD_DEVICE_ID_HIGH = 9
SCAN_RECORD_DEVICE_ID_LOW = 10
SCAN_RECORD_ROWS = 17
SCAN_RECORD_COLS_HIGH = 18
SCAN_RECORD_COLS_LOW = 19
SCAN_RECORD_COLOR_TYPE = 20
SCAN_RECORD_FW_VERSION = 21

# Text-Encoding Konstanten
TEXT_HEADER_SIZE = 24       # 24 Null-Bytes als Header
TEXT_WIDTHS_PAD_SIZE = 80   # Char-Widths werden auf 80 Bytes gepaddet
TEXT_CHUNK_SIZE = 128       # Daten werden in 128-Byte-Chunks aufgeteilt

# Font-Dateien: Bytes pro Zeichen
FONT_UNICODE12_BYTES_PER_CHAR = 24   # UNICODE12: 24 Bytes/Zeichen (12 Zeilen)
FONT_UNICODE16_BYTES_PER_CHAR = 32   # UNICODE16: 32 Bytes/Zeichen (16 Zeilen)

# Display-Modi (typische Werte aus der App)
MODE_STATIC = 0
MODE_SCROLL_LEFT = 1
MODE_SCROLL_RIGHT = 2
MODE_SCROLL_UP = 3
MODE_SCROLL_DOWN = 4
MODE_FLASH = 5
MODE_SNOWFLAKE = 6
MODE_CURTAIN = 7
MODE_LASER = 8

MODE_NAMES = {
    MODE_STATIC: "Statisch",
    MODE_SCROLL_LEFT: "Scrollen Links",
    MODE_SCROLL_RIGHT: "Scrollen Rechts",
    MODE_SCROLL_UP: "Scrollen Hoch",
    MODE_SCROLL_DOWN: "Scrollen Runter",
    MODE_FLASH: "Blinken",
    MODE_SNOWFLAKE: "Schneeflocke",
    MODE_CURTAIN: "Vorhang",
    MODE_LASER: "Laser",
}

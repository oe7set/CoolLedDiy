"""
Kommando-Builder für das CoolLed BLE-Protokoll.

Baut die einzelnen Steuerkommandos auf und verpackt sie als Frame-Pakete.
Basiert auf Light1248Utils.java Methoden: getModeDataString, getSpeedDataString,
getBrightDataString, getSwitchDataString, getBeginDataString, getDrawDataString.
"""

from coolled.protocol.constants import (
    CMD_BEGIN_TRANSFER,
    CMD_BRIGHTNESS,
    CMD_DRAW,
    CMD_MODE,
    CMD_SPEED,
    CMD_SWITCH,
)
from coolled.protocol.framing import frame_packet


def cmd_mode(mode: int) -> bytes:
    """Setzt den Display-Modus (z.B. Scrollen, Blinken, Statisch).

    Entspricht getModeDataString() in Light1248Utils.java:83-88.
    Payload: [CMD_MODE, mode_byte]
    """
    return frame_packet(bytes([CMD_MODE, mode & 0xFF]))


def cmd_speed(speed: int) -> bytes:
    """Setzt die Scroll-/Animations-Geschwindigkeit.

    Entspricht getSpeedDataString() in Light1248Utils.java:90-95.
    Payload: [CMD_SPEED, speed_byte]
    """
    return frame_packet(bytes([CMD_SPEED, speed & 0xFF]))


def cmd_brightness(brightness: int) -> bytes:
    """Setzt die Display-Helligkeit.

    Entspricht getBrightDataString() in Light1248Utils.java:97-102.
    Payload: [CMD_BRIGHTNESS, brightness_byte]
    """
    return frame_packet(bytes([CMD_BRIGHTNESS, brightness & 0xFF]))


def cmd_switch(on: bool) -> bytes:
    """Schaltet das Display ein/aus.

    Entspricht getSwitchDataString() in Light1248Utils.java:104-113.
    Payload: [CMD_SWITCH, 0x01 (ein) oder 0x00 (aus)]
    """
    return frame_packet(bytes([CMD_SWITCH, 0x01 if on else 0x00]))


def cmd_begin_transfer() -> bytes:
    """Signalisiert den Beginn einer Datenübertragung.

    Entspricht getBeginDataString() in Light1248Utils.java:437-441.
    Payload: [CMD_BEGIN_TRANSFER]
    """
    return frame_packet(bytes([CMD_BEGIN_TRANSFER]))


def cmd_draw(bitmap_data: bytes) -> bytes:
    """Sendet Bitmap-Daten direkt an das Display (Draw-Modus).

    Entspricht getDrawDataString() in Light1248Utils.java:76-81.
    Payload: [CMD_DRAW] + bitmap_data

    bitmap_data enthält die spaltenweise codierten Pixel-Daten.
    Für ein 12×48 Panel: 96 Bytes (2 Bytes pro Spalte × 48 Spalten).
    """
    return frame_packet(bytes([CMD_DRAW]) + bitmap_data)


def cmd_raw(payload: bytes) -> bytes:
    """Verpackt beliebige Payload-Daten in ein Frame-Paket.

    Nützlich für den Debug-Tab um manuell Kommandos zu testen.
    """
    return frame_packet(payload)

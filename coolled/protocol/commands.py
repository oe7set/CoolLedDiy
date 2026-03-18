"""
Kommando-Builder für das CoolLed BLE-Protokoll.

Baut die einzelnen Steuerkommandos auf und verpackt sie als Frame-Pakete.
Basiert auf Light1248Utils.java Methoden: getModeDataString, getSpeedDataString,
getBrightDataString, getSwitchDataString, getBeginDataString, getDrawDataString.
"""

from datetime import datetime

from coolled.protocol.constants import (
    CMD_ANIMATION,
    CMD_BEGIN_TRANSFER,
    CMD_BRIGHTNESS,
    CMD_DEVICE_INFO,
    CMD_DRAW,
    CMD_MIRROR,
    CMD_MODE,
    CMD_SPEED,
    CMD_SWITCH,
    CMD_SYNC_TIME,
    TEXT_CHUNK_SIZE,
    TEXT_HEADER_SIZE,
)
from coolled.protocol.framing import frame_packet, int_to_2bytes_be


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


def cmd_draw_packets(bitmap_data: bytes) -> list[bytes]:
    """Baut Draw-Pakete mit Chunk-Protokoll (wie Text/Animation).

    Entspricht getIconDataStrings() in Light1248Utils.java:353-392.
    Nutzt das gleiche Chunk-Format wie Text und Animation:
    24-Byte-Header + Datenlänge(2B BE) + Bitmap-Daten, aufgeteilt in 128-Byte-Chunks.

    Args:
        bitmap_data: Spaltenweise codierte Pixel-Daten

    Returns:
        Liste von Frame-Paketen, bereit zum Senden
    """
    # Gesamtdaten: 24 Null-Header + Datenlänge(2B BE) + Bitmap
    data_length = len(bitmap_data)
    all_data = bytearray(TEXT_HEADER_SIZE)  # 24 Null-Bytes
    all_data.extend(int_to_2bytes_be(data_length))
    all_data.extend(bitmap_data)

    # In 128-Byte-Chunks aufteilen
    chunks = []
    for i in range(0, len(all_data), TEXT_CHUNK_SIZE):
        chunks.append(bytes(all_data[i:i + TEXT_CHUNK_SIZE]))

    # Pro Chunk: Metadata + Checksum + CMD_DRAW + Frame
    total_data_length = int_to_2bytes_be(len(all_data))
    packets = []

    for chunk_index, chunk in enumerate(chunks):
        # Chunk-Prefix: [0x00] + total_len(2B) + chunk_idx(2B) + chunk_size(1B)
        chunk_prefix = (
            bytes([0x00])
            + total_data_length
            + int_to_2bytes_be(chunk_index)
            + bytes([len(chunk)])
        )
        chunk_with_prefix = chunk_prefix + chunk
        checksum = _xor_checksum(chunk_with_prefix)
        chunk_with_checksum = chunk_with_prefix + bytes([checksum])

        payload = bytes([CMD_DRAW]) + chunk_with_checksum
        packets.append(frame_packet(payload))

    return packets


def cmd_raw(payload: bytes) -> bytes:
    """Verpackt beliebige Payload-Daten in ein Frame-Paket.

    Nützlich für den Debug-Tab um manuell Kommandos zu testen.
    """
    return frame_packet(payload)


def cmd_sync_time(dt: datetime | None = None) -> bytes:
    """Synchronisiert die Uhrzeit mit dem Gerät.

    Entspricht getSynchronizeTime() in CoolledUXUtils.java:4036-4089.
    Payload: [0x09, year-2000, month, day, weekday, hour, minute, second]
    Wochentag: 1=Mo, 2=Di, ..., 7=So (isoweekday() passt direkt).

    Args:
        dt: Zeitpunkt zum Senden (Standard: aktuelle Systemzeit)
    """
    if dt is None:
        dt = datetime.now()
    year_offset = (dt.year - 2000) & 0xFF
    payload = bytes([
        CMD_SYNC_TIME,
        year_offset,
        dt.month,
        dt.day,
        dt.isoweekday(),  # 1=Mo ... 7=So
        dt.hour,
        dt.minute,
        dt.second,
    ])
    return frame_packet(payload)


def cmd_mirror(enabled: bool) -> bytes:
    """Spiegelt die Display-Ausgabe.

    Entspricht getSetMirror() in CoolledUXUtils.java:3958-3966.
    Payload: [0x0C, 0x01 (an) oder 0x00 (aus)]
    """
    return frame_packet(bytes([CMD_MIRROR, 0x01 if enabled else 0x00]))


def cmd_device_info() -> bytes:
    """Fragt Geräteinformationen ab.

    Entspricht getDeviceInfo() in CoolledUXUtils.java:3934-3937.
    Payload: [0x1F]
    """
    return frame_packet(bytes([CMD_DEVICE_INFO]))


def _xor_checksum(data: bytes) -> int:
    """Berechnet die XOR-Checksum über alle Bytes (Startwert 0x00)."""
    result = 0x00
    for b in data:
        result ^= b
    return result


def cmd_animation_packets(frames: list[bytes], speed: int = 100) -> list[bytes]:
    """Baut Animation-Pakete aus mehreren Bitmap-Frames.

    Entspricht getSendDataAnimationData() in Light1248Utils.java:825-853.
    Nutzt getSendDataWithTypeStrings("04",...) für das Chunk-Format.

    Args:
        frames: Liste von Bitmap-Daten (column-encoded) pro Frame
        speed: Animations-Geschwindigkeit in ms (16-Bit, High/Low)

    Returns:
        Liste von Frame-Paketen, bereit zum Senden
    """
    # Gesamtdaten: 24 Null-Header + Frame-Count + Speed(2B) + alle Bitmaps
    all_data = bytearray(TEXT_HEADER_SIZE)  # 24 Null-Bytes
    all_data.append(len(frames) & 0xFF)
    all_data.append((speed >> 8) & 0xFF)
    all_data.append(speed & 0xFF)
    for frame_data in frames:
        all_data.extend(frame_data)

    # In 128-Byte-Chunks aufteilen
    chunks = []
    for i in range(0, len(all_data), TEXT_CHUNK_SIZE):
        chunks.append(bytes(all_data[i:i + TEXT_CHUNK_SIZE]))

    # Pro Chunk: Metadata + Checksum + CMD_ANIMATION + Frame
    total_data_length = int_to_2bytes_be(len(all_data))
    packets = []

    for chunk_index, chunk in enumerate(chunks):
        # Chunk-Prefix: [0x00] + total_len(2B) + chunk_idx(2B) + chunk_size(1B)
        chunk_prefix = (
            bytes([0x00])
            + total_data_length
            + int_to_2bytes_be(chunk_index)
            + bytes([len(chunk)])
        )
        chunk_with_prefix = chunk_prefix + chunk
        checksum = _xor_checksum(chunk_with_prefix)
        chunk_with_checksum = chunk_with_prefix + bytes([checksum])

        payload = bytes([CMD_ANIMATION]) + chunk_with_checksum
        packets.append(frame_packet(payload))

    return packets

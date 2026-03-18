"""
Erweiterte Kommando-Builder für CoolLed M/U/UX-Geräte.

Diese Geräte verwenden ein anderes Paketformat als Light1248:
- 1024-Byte Chunk-Größe (statt 128)
- 4-Byte Längenfelder (statt 2)
- 2-Byte Chunk-Size (statt 1)
- LZSS-Kompression der Nutzdaten
- CRC-32 Checksumme im Start-Paket
- Programm-basiertes Senden (Start-Paket + Daten-Pakete)

Basiert auf CoolledMUtils.java Methoden:
- getDataPacket() (Zeilen 937-965)
- getStartDataForProgram() (Zeilen 1521-1529)
- getDataWithProgram() (Zeilen 1531-1542)
- getDataResult() (Zeilen 1544-1552)
"""

from coolled.protocol.constants import (
    CMD_M_BRIGHTNESS,
    CMD_M_DATA,
    CMD_M_START,
    CMD_M_SWITCH,
    M_CHUNK_SIZE,
)
from coolled.protocol.crc32 import crc32_coolled_bytes
from coolled.protocol.framing import frame_packet, int_to_2bytes_be
from coolled.protocol.lzss import lzss_compress


def _int_to_4bytes_be(value: int) -> bytes:
    """Konvertiert einen Integer in 4 Bytes Big-Endian.

    Entspricht getHexListStringForIntWithFourByte() in LightUtils.java.
    """
    return value.to_bytes(4, byteorder="big")


def _xor_checksum(data: bytes) -> int:
    """Berechnet die XOR-Checksum über alle Bytes (Startwert 0x00)."""
    result = 0x00
    for b in data:
        result ^= b
    return result


def build_start_packet(data: bytes, content_count: int, show_count: int) -> bytes:
    """Baut das Start-Paket für M/U/UX-Programm-Übertragung.

    Entspricht getStartDataForProgram() in CoolledMUtils.java:1521-1528.
    Wird VOR den Daten-Paketen gesendet und enthält CRC + Gesamtlänge.

    Format: [CMD_M_START] + CRC32(4B) + total_len(4B) + content_count(1B) + show_count(1B)

    Args:
        data: Unkomprimierte Programm-Daten (für CRC-Berechnung und Länge)
        content_count: Anzahl der Inhalte im Programm
        show_count: Anzeige-Zähler

    Returns:
        Fertiges Frame-Paket
    """
    crc = crc32_coolled_bytes(data)
    total_len = _int_to_4bytes_be(len(data))
    payload = (
        bytes([CMD_M_START])
        + crc
        + total_len
        + bytes([content_count & 0xFF, show_count & 0xFF])
    )
    return frame_packet(payload)


def build_data_packets(data: bytes) -> list[bytes]:
    """Teilt komprimierte Daten in 1024-Byte Pakete auf (M/U/UX-Format).

    Entspricht getDataPacket() in CoolledMUtils.java:937-965.

    Chunk-Format pro Paket:
      [CMD_M_DATA] + [0x00] + total_len(4B BE) + chunk_idx(2B BE)
      + chunk_size(2B BE) + chunk_data + XOR-Checksum

    Unterschiede zu Light1248:
    - 1024 Bytes statt 128 pro Chunk
    - 4-Byte total_len statt 2-Byte
    - 2-Byte chunk_size statt 1-Byte

    Args:
        data: Bereits LZSS-komprimierte Daten

    Returns:
        Liste von Frame-Paketen, bereit zum Senden
    """
    # In 1024-Byte-Chunks aufteilen
    chunks = []
    for i in range(0, len(data), M_CHUNK_SIZE):
        chunks.append(data[i:i + M_CHUNK_SIZE])

    total_data_length = _int_to_4bytes_be(len(data))
    packets = []

    for chunk_index, chunk in enumerate(chunks):
        # Chunk-Prefix: [0x00] + total_len(4B) + chunk_idx(2B) + chunk_size(2B)
        chunk_prefix = (
            bytes([0x00])
            + total_data_length
            + int_to_2bytes_be(chunk_index)
            + int_to_2bytes_be(len(chunk))
        )
        chunk_with_prefix = chunk_prefix + chunk

        # XOR-Checksum über Prefix + Daten
        checksum = _xor_checksum(chunk_with_prefix)
        chunk_with_checksum = chunk_with_prefix + bytes([checksum])

        # CMD_M_DATA + Chunk → Frame
        payload = bytes([CMD_M_DATA]) + chunk_with_checksum
        packets.append(frame_packet(payload))

    return packets


def build_program_data(content_data: bytes, content_count: int = 1, show_count: int = 0) -> bytes:
    """Verpackt Content-Daten im Programm-Format.

    Entspricht getDataWithProgram() in CoolledMUtils.java:1531-1541.

    Format: [8 Null-Bytes] + content_count(1B) + show_count(1B) + content_data

    Args:
        content_data: Die eigentlichen Nutzdaten (Text-Bitmap, Bild, etc.)
        content_count: Anzahl der Inhalte (typisch 1)
        show_count: Anzeige-Zähler (typisch 0)

    Returns:
        Programm-Daten (noch nicht komprimiert)
    """
    header = bytes(8)  # 8 Null-Bytes
    return header + bytes([content_count & 0xFF, show_count & 0xFF]) + content_data


def build_program_transfer(
    program_data: bytes,
    content_count: int = 1,
    show_count: int = 0,
) -> tuple[bytes, list[bytes]]:
    """Baut die komplette Programm-Übertragung (Start-Paket + Daten-Pakete).

    Entspricht getDataResult() in CoolledMUtils.java:1544-1552.

    Ablauf:
    1. Start-Paket mit CRC und Gesamtlänge (unkomprimierte Daten)
    2. Daten komprimieren mit LZSS
    3. Komprimierte Daten in 1024-Byte-Chunks aufteilen

    Args:
        program_data: Unkomprimierte Programm-Daten (Ergebnis von build_program_data())
        content_count: Anzahl Inhalte
        show_count: Anzeige-Zähler

    Returns:
        Tuple (start_packet, data_packets) - start_packet zuerst senden
    """
    # Start-Paket enthält CRC und Länge der unkomprimierten Daten
    start_packet = build_start_packet(program_data, content_count, show_count)

    # Daten komprimieren und in Chunks aufteilen
    compressed = lzss_compress(program_data)
    data_packets = build_data_packets(compressed)

    return start_packet, data_packets


def cmd_brightness_m(brightness: int) -> bytes:
    """Setzt die Helligkeit (M/U/UX-Geräte).

    Entspricht getSetBrightness() in CoolledMUtils.java:1571-1576.
    Nutzt Kommando-Byte 0x04 statt 0x08.
    """
    return frame_packet(bytes([CMD_M_BRIGHTNESS, brightness & 0xFF]))


def cmd_switch_m(on: bool) -> bytes:
    """Schaltet das Display ein/aus (M/U/UX-Geräte).

    Entspricht getSwitchData() in CoolledMUtils.java:1560-1569.
    Nutzt Kommando-Byte 0x05 statt 0x09.
    """
    return frame_packet(bytes([CMD_M_SWITCH, 0x01 if on else 0x00]))

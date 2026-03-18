"""
Text-Encoding für das CoolLed BLE-Protokoll.

Wandelt Text in sendefertige BLE-Pakete um:
  1. Font-Bitmap pro Zeichen laden
  2. Header + Text-Length + Char-Widths (gepaddet auf 80) + Data-Length + Bitmap
  3. In 128-Byte-Chunks aufteilen
  4. Pro Chunk: Metadata + XOR-Checksum
  5. CMD_TEXT Prefix + Frame

Basiert auf Light1248Utils.java:297-351 (getTextDataStrings).
"""

from coolled.fonts.font_reader import FontReader
from coolled.protocol.constants import (
    CMD_TEXT,
    TEXT_CHUNK_SIZE,
    TEXT_HEADER_SIZE,
    TEXT_WIDTHS_PAD_SIZE,
)
from coolled.protocol.framing import frame_packet, int_to_2bytes_be


def _xor_checksum(data: bytes) -> int:
    """Berechnet die XOR-Checksum über alle Bytes.

    Entspricht convertEnd() in Light1248Utils.java:428-434.
    Startwert ist 0x00, dann XOR mit jedem Byte.
    """
    result = 0x00
    for b in data:
        result ^= b
    return result


def encode_text_packets(text: str, font_reader: FontReader, use_font_16: bool = False) -> list[bytes]:
    """Kodiert einen Text in eine Liste von sendefertigen BLE-Paketen.

    Entspricht getTextDataStrings() in Light1248Utils.java:297-351.

    Args:
        text: Der zu sendende Text
        font_reader: FontReader-Instanz zum Laden der Font-Bitmaps
        use_font_16: True für UNICODE16 (16-Zeilen-Panels), False für UNICODE12

    Returns:
        Liste von Frame-Paketen (bytes), bereit zum Senden über BLE.
    """
    # 1. Font-Daten laden
    if use_font_16:
        font_data, char_widths = font_reader.read_text_16(text)
    else:
        font_data, char_widths = font_reader.read_text_12(text)

    # 2. Header bauen (Ref: Light1248Utils.java:313-323)
    # 24 Null-Bytes als Header
    header = bytes(TEXT_HEADER_SIZE)

    # Text-Länge als 1 Byte (getHexListStringForInt)
    text_length_byte = bytes([len(text) & 0xFF])

    # Char-Widths auf 80 Bytes padden (Ref: Light1248Utils.java:305-310)
    widths_bytes = bytes(char_widths)
    if len(widths_bytes) < TEXT_WIDTHS_PAD_SIZE:
        widths_bytes += bytes(TEXT_WIDTHS_PAD_SIZE - len(widths_bytes))

    # Data-Length als 2 Bytes BE (getDataStringLength)
    data_length = int_to_2bytes_be(len(font_data))

    # Gesamtdaten zusammenbauen
    all_data = header + text_length_byte + widths_bytes + data_length + font_data

    # 3. In 128-Byte-Chunks aufteilen (Ref: Light1248Utils.java:325-336)
    chunks = []
    for i in range(0, len(all_data), TEXT_CHUNK_SIZE):
        chunks.append(all_data[i:i + TEXT_CHUNK_SIZE])

    # 4. Pro Chunk: Metadata + Checksum + CMD_TEXT + Frame (Ref: Light1248Utils.java:337-349)
    total_data_length = int_to_2bytes_be(len(all_data))
    packets = []

    for chunk_index, chunk in enumerate(chunks):
        # Chunk-Prefix: [0x00] + total_data_length(2B) + chunk_index(2B) + chunk_size(1B)
        chunk_prefix = (
            bytes([0x00])
            + total_data_length
            + int_to_2bytes_be(chunk_index)
            + bytes([len(chunk)])
        )

        # Chunk-Daten mit Prefix
        chunk_with_prefix = chunk_prefix + chunk

        # XOR-Checksum über den gesamten Chunk (inkl. Prefix)
        checksum = _xor_checksum(chunk_with_prefix)
        chunk_with_checksum = chunk_with_prefix + bytes([checksum])

        # CMD_TEXT Prefix + Frame
        payload = bytes([CMD_TEXT]) + chunk_with_checksum
        packets.append(frame_packet(payload))

    return packets

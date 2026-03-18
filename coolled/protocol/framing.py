"""
Paket-Framing für das CoolLed BLE-Protokoll.

Implementiert Escape-Encoding und Frame-Struktur basierend auf
Light1248Utils.java:443-466 (getSendDataWithInfo, convertData).

Frame-Aufbau:
  0x01 | escaped(length_2B_BE + payload) | 0x03

Escape-Regeln:
  Bytes im Bereich 0x01-0x03 werden ersetzt durch [0x02, byte ^ 0x04]
"""

from coolled.protocol.constants import ESCAPE_BYTE, ESCAPE_XOR, FRAME_END, FRAME_START


def int_to_2bytes_be(value: int) -> bytes:
    """Konvertiert einen Integer in 2 Bytes Big-Endian.

    Entspricht getDataStringLength() / getHexListStringForIntWithTwo() in LightUtils.java.
    """
    return bytes([(value >> 8) & 0xFF, value & 0xFF])


def escape_data(data: bytes) -> bytes:
    """Escaped Bytes im Bereich 0x01-0x03 im Payload.

    Entspricht convertData() in Light1248Utils.java:454-466.
    Bytes 0x01, 0x02, 0x03 werden zu [0x02, byte ^ 0x04].
    """
    result = bytearray()
    for b in data:
        if 0x01 <= b <= 0x03:
            result.append(ESCAPE_BYTE)
            result.append(b ^ ESCAPE_XOR)
        else:
            result.append(b)
    return bytes(result)


def unescape_data(data: bytes) -> bytes:
    """Entfernt Escape-Encoding aus Daten.

    Umkehrung von escape_data(): [0x02, X] → X ^ 0x04.
    Entspricht recoverData() in Light1248Utils.java:468-487.
    """
    result = bytearray()
    i = 0
    while i < len(data):
        if data[i] == ESCAPE_BYTE and i + 1 < len(data):
            result.append(data[i + 1] ^ ESCAPE_XOR)
            i += 2
        else:
            result.append(data[i])
            i += 1
    return bytes(result)


def frame_packet(payload: bytes) -> bytes:
    """Baut ein vollständiges Frame-Paket.

    Entspricht getSendDataWithInfo() in Light1248Utils.java:443-452.
    Struktur: FRAME_START | escaped(length_2B + payload) | FRAME_END
    """
    length_bytes = int_to_2bytes_be(len(payload))
    inner = length_bytes + payload
    escaped = escape_data(inner)
    return bytes([FRAME_START]) + escaped + bytes([FRAME_END])


def unframe_packet(data: bytes) -> bytes | None:
    """Extrahiert den Payload aus einem Frame-Paket.

    Entfernt Start/End-Marker, un-escaped die Daten, entfernt Length-Prefix.
    Gibt None zurück wenn das Frame ungültig ist.
    """
    if len(data) < 4:
        return None
    if data[0] != FRAME_START or data[-1] != FRAME_END:
        return None

    # Start/End-Marker entfernen
    inner = data[1:-1]
    # Escape-Encoding rückgängig machen
    unescaped = unescape_data(inner)

    if len(unescaped) < 2:
        return None

    # Length-Prefix (2 Bytes) entfernen
    payload = unescaped[2:]
    return payload

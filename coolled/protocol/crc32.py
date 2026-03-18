"""
CoolLed-spezifischer CRC-32 Algorithmus.

ACHTUNG: Dies ist KEIN Standard-CRC-32! Es ist ein eigener Algorithmus
mit Polynom 0x04C11DB7 und einer Bit-für-Bit-Verarbeitung die sich von
zlib.crc32() unterscheidet.

Basiert auf CoolledMUtils.CrcCode.getCrc32CheckCode2() (Zeilen 588-604).
"""

# CRC-32 Polynom (dezimal: 79764919)
CRC32_POLYNOMIAL = 0x04C11DB7


def crc32_coolled(data: bytes) -> int:
    """Berechnet den CoolLed-spezifischen CRC-32.

    Algorithmus (aus getCrc32CheckCode2):
    - Startwert: 0xFFFFFFFF (-1 signed)
    - Für jedes Byte: 32 Iterationen mit Bit-Shift und XOR
    - Das Byte wird an den unteren 8 Bits eingespeist (Bits 7-0)
    - Bits 31-8 des Input sind immer 0 (Byte-Wert max 255)

    Args:
        data: Eingabedaten

    Returns:
        32-Bit CRC-Wert (unsigned)
    """
    crc = 0xFFFFFFFF
    for byte_val in data:
        val = byte_val & 0xFF
        msb = 0x80000000  # Integer.MIN_VALUE in Java
        for _ in range(32):
            # CRC shift left, XOR mit Polynom wenn MSB gesetzt war
            if crc & 0x80000000:
                crc = ((crc << 1) ^ CRC32_POLYNOMIAL) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
            # Input-Bit einspeisen
            if val & msb:
                crc ^= CRC32_POLYNOMIAL
            msb >>= 1
    return crc


def crc32_coolled_bytes(data: bytes) -> bytes:
    """Berechnet CRC-32 und gibt das Ergebnis als 4 Bytes Big-Endian zurück.

    Entspricht CrcCode.getCrcCode() → getHexListStringForIntWithFourByte().
    """
    crc = crc32_coolled(data)
    return crc.to_bytes(4, byteorder="big")

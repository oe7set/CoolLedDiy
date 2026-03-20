"""
Gerätetyp-Erkennung für CoolLed BLE-Geräte.

Erkennt die Gerätefamilie anhand des BLE-Namens, um das korrekte
Protokoll (Light1248, 536, CoolledM, U, UX) auszuwählen.

Basiert auf DeviceManager.java Geräte-Konstanten (Zeilen 65-125).
"""

from enum import Enum


class DeviceFamily(Enum):
    """Protokoll-Familie eines CoolLed Geräts.

    Jede Familie hat ein eigenes Paketformat und Kommando-Bytes:
    - LIGHT_1248: Einfaches 128-Byte-Chunk-Format, kein LZSS/CRC
    - LIGHT_536: Wie 1248, aber mit begin_transfer + 50ms Delay
    - COOLED_M: 1024-Byte-Chunks, LZSS, CRC-32, Programm-Format
    - COOLED_U: Wie M (inkl. UD-Variante iLedBike)
    - COOLED_UX: Wie M, zusätzlich Zeitsync und erweiterte Kommandos
    """
    LIGHT_1248 = "light1248"
    LIGHT_536 = "light536"
    COOLED_M = "cooledm"
    COOLED_U = "cooledu"
    COOLED_UX = "cooledux"


# Namens-Prefixe → Gerätefamilie
# Reihenfolge ist wichtig: spezifischere Prefixe zuerst (z.B. "CoolLEDUX" vor "CoolLEDU")
_NAME_PREFIXES: list[tuple[str, DeviceFamily]] = [
    # UX-Familie (vor U, da "CoolLEDUX" mit "CoolLEDU" beginnt)
    ("CoolLEDUX", DeviceFamily.COOLED_UX),
    ("iLedClock", DeviceFamily.COOLED_UX),
    ("iLedOpen", DeviceFamily.COOLED_UX),
    ("iLedHatC", DeviceFamily.COOLED_UX),
    ("iDevilEyes", DeviceFamily.COOLED_UX),
    ("iLedHat", DeviceFamily.COOLED_UX),
    # U-Familie (inkl. UD-Variante)
    ("CoolLEDU", DeviceFamily.COOLED_U),
    ("iLedBike", DeviceFamily.COOLED_U),
    # M-Familie
    ("CoolLEDM", DeviceFamily.COOLED_M),
    # 536-Familie
    ("CoolLED536", DeviceFamily.LIGHT_536),
    # 1248-Familie (Default für alle anderen CoolLED-Varianten)
    ("CoolLEDX", DeviceFamily.LIGHT_1248),
    ("CoolLEDA", DeviceFamily.LIGHT_1248),
    ("CoolLEDS", DeviceFamily.LIGHT_1248),
    ("CoolLED", DeviceFamily.LIGHT_1248),
]


def detect_device_family(name: str) -> DeviceFamily:
    """Erkennt die Gerätefamilie anhand des BLE-Namens.

    Args:
        name: BLE-Gerätename (z.B. "CoolLEDM", "CoolLEDUX-1234")

    Returns:
        Erkannte DeviceFamily, Default ist LIGHT_1248
    """
    for prefix, family in _NAME_PREFIXES:
        if name.startswith(prefix):
            return family
    return DeviceFamily.LIGHT_1248


def uses_advanced_protocol(family: DeviceFamily) -> bool:
    """Prüft ob die Gerätefamilie das erweiterte Protokoll (LZSS/CRC/1024B) nutzt."""
    return family in (DeviceFamily.COOLED_M, DeviceFamily.COOLED_U, DeviceFamily.COOLED_UX)


def is_ux_family(family: DeviceFamily) -> bool:
    """Prüft ob die Gerätefamilie CoolLedUX ist (RGB444-Pixelformat, UX-Kommandos)."""
    return family == DeviceFamily.COOLED_UX


def uses_begin_transfer(family: DeviceFamily) -> bool:
    """Prüft ob die Gerätefamilie begin_transfer vor Daten erwartet.

    Light1248 sendet Text/Draw direkt (TextIconEvent), ohne begin_transfer.
    Light536 sendet begin_transfer + 50ms Delay + Daten.
    M/U/UX nutzen das Programm-Format (start_packet + data_packets).
    """
    return family == DeviceFamily.LIGHT_536

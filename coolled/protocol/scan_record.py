"""
BLE Scan-Record Parser für CoolLed Geräte.

Extrahiert Geräteinformationen aus dem 31-Byte Scan-Record (Advertisement Data).
Basiert auf BleDeviceSimulator.java:45-106 (generateScanRecord).

Byte-Layout:
  [9:10]  - Device ID (Big-Endian)
  [17]    - Zeilen (rows)
  [18:19] - Spalten (columns, Big-Endian)
  [20]    - Farb-Typ (0=single, 1=7-color, 2=colorful, 3=UX, 4=clock)
  [21]    - Firmware-Version
"""

from dataclasses import dataclass

from coolled.protocol.constants import (
    COLOR_CLOCK,
    COLOR_COLORFUL,
    COLOR_SEVEN,
    COLOR_SINGLE,
    COLOR_UX,
    SCAN_RECORD_COLS_HIGH,
    SCAN_RECORD_COLS_LOW,
    SCAN_RECORD_COLOR_TYPE,
    SCAN_RECORD_DEVICE_ID_HIGH,
    SCAN_RECORD_DEVICE_ID_LOW,
    SCAN_RECORD_FW_VERSION,
    SCAN_RECORD_ROWS,
)


@dataclass
class ScanRecordInfo:
    """Geparste Informationen aus einem CoolLed Scan-Record."""

    device_id: int       # Geräte-ID (2 Bytes)
    rows: int            # Anzahl Zeilen der LED-Matrix
    columns: int         # Anzahl Spalten der LED-Matrix
    color_type: int      # Farb-Typ (0-4)
    fw_version: int      # Firmware-Version

    @property
    def color_type_name(self) -> str:
        """Gibt den lesbaren Namen des Farb-Typs zurück."""
        names = {
            COLOR_SINGLE: "Single",
            COLOR_SEVEN: "7-Color",
            COLOR_COLORFUL: "Colorful",
            COLOR_UX: "UX",
            COLOR_CLOCK: "Clock",
        }
        return names.get(self.color_type, f"Unknown({self.color_type})")

    @property
    def matrix_size(self) -> str:
        """Gibt die Matrix-Größe als String zurück, z.B. '16x64'."""
        return f"{self.rows}x{self.columns}"


def parse_scan_record(data: bytes) -> ScanRecordInfo | None:
    """Parst einen 31-Byte Scan-Record in ScanRecordInfo.

    Gibt None zurück wenn die Daten zu kurz oder ungültig sind.
    """
    if len(data) < 22:
        return None

    device_id = (data[SCAN_RECORD_DEVICE_ID_HIGH] << 8) | data[SCAN_RECORD_DEVICE_ID_LOW]
    rows = data[SCAN_RECORD_ROWS]
    columns = (data[SCAN_RECORD_COLS_HIGH] << 8) | data[SCAN_RECORD_COLS_LOW]
    color_type = data[SCAN_RECORD_COLOR_TYPE]
    fw_version = data[SCAN_RECORD_FW_VERSION]

    return ScanRecordInfo(
        device_id=device_id,
        rows=rows,
        columns=columns,
        color_type=color_type,
        fw_version=fw_version,
    )

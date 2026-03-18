"""
Font-Reader für CoolLed Binär-Font-Dateien (UNICODE12, UNICODE16).

Liest Zeichen-Bitmaps direkt aus den Font-Dateien per Seek/Read.
Basiert auf FontUtils.java:3135-3208 (readUnicode1248, readUnicode16).

Font-Format:
  - UNICODE12: 24 Bytes pro Zeichen, Offset = char_code × 24
  - UNICODE16: 32 Bytes pro Zeichen, Offset = char_code × 32
  - Direkter Zugriff über Datei-Seek auf (char_code × bytes_per_char)
"""

import sys
from pathlib import Path

from coolled.protocol.constants import (
    FONT_UNICODE12_BYTES_PER_CHAR,
    FONT_UNICODE16_BYTES_PER_CHAR,
)

# Standard-Pfad zu den Font-Dateien (PyInstaller-kompatibel)
if getattr(sys, '_MEIPASS', None):
    _DEFAULT_ASSETS_DIR = Path(sys._MEIPASS) / "coolled" / "fonts" / "data"
else:
    _DEFAULT_ASSETS_DIR = Path(__file__).parent / "data"


class FontReader:
    """Liest Zeichen-Bitmaps aus CoolLed Binär-Font-Dateien.

    Unterstützt UNICODE12 (12-Zeilen-Panels) und UNICODE16 (16-Zeilen-Panels).
    """

    def __init__(self, assets_dir: Path | str | None = None):
        """Initialisiert den FontReader mit dem Pfad zum Assets-Verzeichnis.

        Args:
            assets_dir: Pfad zum Verzeichnis mit UNICODE12/UNICODE16 Dateien.
                        Standard: coolled1248decomp/resources/assets/
        """
        self.assets_dir = Path(assets_dir) if assets_dir else _DEFAULT_ASSETS_DIR

    def _read_char_from_file(self, filename: str, char_code: int, bytes_per_char: int) -> bytes:
        """Liest die Bitmap-Daten eines einzelnen Zeichens aus einer Font-Datei.

        Args:
            filename: Name der Font-Datei (z.B. "UNICODE12")
            char_code: Unicode-Codepoint des Zeichens
            bytes_per_char: Anzahl Bytes pro Zeichen in dieser Font-Datei

        Returns:
            Bitmap-Daten als bytes (bytes_per_char lang)
        """
        filepath = self.assets_dir / filename
        offset = char_code * bytes_per_char

        with open(filepath, "rb") as f:
            f.seek(offset)
            data = f.read(bytes_per_char)

        # Falls am Ende der Datei weniger Bytes gelesen werden, mit 0x00 auffüllen
        if len(data) < bytes_per_char:
            data = data + b'\x00' * (bytes_per_char - len(data))

        return data

    def read_char_12(self, char: str) -> bytes:
        """Liest die 24-Byte Bitmap eines Zeichens aus UNICODE12.

        Entspricht readUnicode1248() in FontUtils.java:3135-3148.
        """
        return self._read_char_from_file("UNICODE12", ord(char), FONT_UNICODE12_BYTES_PER_CHAR)

    def read_char_16(self, char: str) -> bytes:
        """Liest die 32-Byte Bitmap eines Zeichens aus UNICODE16.

        Entspricht readUnicode16() in FontUtils.java:3195-3208.
        """
        return self._read_char_from_file("UNICODE16", ord(char), FONT_UNICODE16_BYTES_PER_CHAR)

    def read_text_12(self, text: str) -> tuple[bytes, list[int]]:
        """Liest die Font-Bitmaps für einen ganzen Text (12-Zeilen-Font).

        Entspricht getFontByteData1248() in FontUtils.java:3492-3504.

        Args:
            text: Der zu rendernde Text

        Returns:
            Tuple aus (bitmap_daten, liste_der_zeichenbreiten).
            bitmap_daten = Konkatenation aller Zeichen-Bitmaps.
            zeichenbreiten = Anzahl Bytes pro Zeichen (immer 24 für UNICODE12).
        """
        all_data = bytearray()
        widths = []
        for char in text:
            char_data = self.read_char_12(char)
            widths.append(len(char_data))
            all_data.extend(char_data)
        return bytes(all_data), widths

    def read_text_16(self, text: str) -> tuple[bytes, list[int]]:
        """Liest die Font-Bitmaps für einen ganzen Text (16-Zeilen-Font).

        Entspricht getFontByteData1632/1664/1696() in FontUtils.java:3506-3560.

        Returns:
            Tuple aus (bitmap_daten, liste_der_zeichenbreiten).
        """
        all_data = bytearray()
        widths = []
        for char in text:
            char_data = self.read_char_16(char)
            widths.append(len(char_data))
            all_data.extend(char_data)
        return bytes(all_data), widths

    def is_available(self, font_name: str = "UNICODE12") -> bool:
        """Prüft ob eine Font-Datei vorhanden ist."""
        return (self.assets_dir / font_name).is_file()

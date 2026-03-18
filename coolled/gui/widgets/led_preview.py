"""
LED-Matrix Vorschau Widget.

Zeigt eine visuelle Vorschau der LED-Matrix als Raster von Punkten.
Unterstützt Aktualisierung mit Bitmap-Daten oder Pillow-Images.
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class LedPreview(QWidget):
    """Custom Paint Widget das eine LED-Matrix als Punkt-Raster darstellt.

    Jede LED wird als kleiner Kreis gezeichnet:
    - An = leuchtend (grün/rot/weiß je nach Einstellung)
    - Aus = dunkel
    """

    # Farben
    COLOR_LED_ON = QColor(0, 255, 50)      # Leuchtend grün
    COLOR_LED_OFF = QColor(30, 30, 30)     # Dunkel
    COLOR_BACKGROUND = QColor(10, 10, 10)  # Fast schwarz

    def __init__(self, rows: int = 16, columns: int = 64, parent: QWidget | None = None):
        super().__init__(parent)
        self._rows = rows
        self._columns = columns
        # Matrix: 2D-Liste [row][col] = True/False
        self._matrix: list[list[bool]] = [
            [False] * columns for _ in range(rows)
        ]
        self.setMinimumHeight(80)

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def columns(self) -> int:
        return self._columns

    def set_size(self, rows: int, columns: int) -> None:
        """Ändert die Matrix-Größe und setzt alle LEDs auf aus."""
        self._rows = rows
        self._columns = columns
        self._matrix = [[False] * columns for _ in range(rows)]
        self.update()

    def set_pixel(self, row: int, col: int, on: bool) -> None:
        """Setzt eine einzelne LED."""
        if 0 <= row < self._rows and 0 <= col < self._columns:
            self._matrix[row][col] = on

    def set_bitmap(self, bitmap: bytes, rows: int | None = None) -> None:
        """Setzt die Matrix aus Bitmap-Daten (Column-Encoding Format).

        Gleiche Kodierung wie image_to_bitmap() in converter.py:
        Pro Spalte: ceil(rows/8) Bytes, MSB = oberste Zeile der Gruppe.
        """
        r = rows or self._rows
        bytes_per_col = (r + 7) // 8

        for col in range(self._columns):
            for byte_group in range(bytes_per_col):
                byte_idx = col * bytes_per_col + byte_group
                if byte_idx >= len(bitmap):
                    return

                byte_val = bitmap[byte_idx]
                start_row = byte_group * 8
                bits = min(8, r - start_row)

                for bit in range(bits):
                    row = start_row + bit
                    if row < self._rows:
                        self._matrix[row][col] = bool(byte_val & (1 << (7 - bit)))

        self.update()

    def clear(self) -> None:
        """Setzt alle LEDs auf aus."""
        self._matrix = [[False] * self._columns for _ in range(self._rows)]
        self.update()

    def paintEvent(self, event) -> None:
        """Zeichnet die LED-Matrix als Punkt-Raster."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Hintergrund
        painter.fillRect(self.rect(), self.COLOR_BACKGROUND)

        if self._rows == 0 or self._columns == 0:
            return

        # LED-Größe berechnen (mit Abstand)
        w = self.width()
        h = self.height()
        led_w = w / self._columns
        led_h = h / self._rows
        led_size = min(led_w, led_h) * 0.8  # 80% für Abstand
        radius = led_size / 2

        # Offset für Zentrierung
        total_w = self._columns * led_w
        total_h = self._rows * led_h
        x_offset = (w - total_w) / 2
        y_offset = (h - total_h) / 2

        painter.setPen(Qt.PenStyle.NoPen)

        for row in range(self._rows):
            for col in range(self._columns):
                cx = x_offset + col * led_w + led_w / 2
                cy = y_offset + row * led_h + led_h / 2

                if self._matrix[row][col]:
                    painter.setBrush(QBrush(self.COLOR_LED_ON))
                else:
                    painter.setBrush(QBrush(self.COLOR_LED_OFF))

                painter.drawEllipse(QRectF(cx - radius, cy - radius, led_size, led_size))

        painter.end()

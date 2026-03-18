"""
Interaktives Pixel-Raster Widget zum Zeichnen auf einer virtuellen LED-Matrix.

Unterstützt Werkzeuge: Zeichnen (Pencil), Radieren (Eraser).
Pixel werden per Klick oder Drag umgeschaltet.
Visueller Stil basiert auf LedPreview (grüne LEDs auf dunklem Hintergrund)
mit zusätzlichem Grid-Overlay.
"""

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


# Werkzeug-Konstanten
TOOL_DRAW = 0
TOOL_ERASE = 1


class DrawingGrid(QWidget):
    """Interaktives Pixel-Raster für LED-Matrix-Zeichnung.

    Jede Zelle entspricht einer LED. Per Mausklick/Drag können LEDs
    ein- oder ausgeschaltet werden.
    """

    # Signals
    grid_changed = Signal()  # Emittiert bei jeder Pixel-Änderung

    # Farben (gleich wie LedPreview)
    COLOR_LED_ON = QColor(0, 255, 50)
    COLOR_LED_OFF = QColor(30, 30, 30)
    COLOR_BACKGROUND = QColor(10, 10, 10)
    COLOR_GRID = QColor(50, 50, 50)  # Grid-Linien

    def __init__(self, rows: int = 16, columns: int = 64, parent: QWidget | None = None):
        super().__init__(parent)
        self._rows = rows
        self._columns = columns
        self._matrix: list[list[bool]] = [[False] * columns for _ in range(rows)]
        self._tool = TOOL_DRAW
        self._drawing = False  # Maus gedrückt
        self._last_cell: tuple[int, int] | None = None  # Letzte bearbeitete Zelle
        self.setMinimumSize(200, 80)
        self.setMouseTracking(False)

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def columns(self) -> int:
        return self._columns

    def set_size(self, rows: int, columns: int) -> None:
        """Ändert die Grid-Größe und setzt alle Pixel auf aus."""
        self._rows = rows
        self._columns = columns
        self._matrix = [[False] * columns for _ in range(rows)]
        self.update()
        self.grid_changed.emit()

    def set_tool(self, tool: int) -> None:
        """Wählt das aktive Werkzeug (TOOL_DRAW oder TOOL_ERASE)."""
        self._tool = tool

    def clear(self) -> None:
        """Setzt alle Pixel auf aus."""
        self._matrix = [[False] * self._columns for _ in range(self._rows)]
        self.update()
        self.grid_changed.emit()

    def get_pixel(self, row: int, col: int) -> bool:
        """Gibt den Zustand eines Pixels zurück."""
        if 0 <= row < self._rows and 0 <= col < self._columns:
            return self._matrix[row][col]
        return False

    def set_pixel(self, row: int, col: int, on: bool) -> None:
        """Setzt ein einzelnes Pixel."""
        if 0 <= row < self._rows and 0 <= col < self._columns:
            self._matrix[row][col] = on

    def get_matrix(self) -> list[list[bool]]:
        """Gibt eine Kopie der internen Matrix zurück."""
        return [row[:] for row in self._matrix]

    def set_matrix(self, matrix: list[list[bool]]) -> None:
        """Setzt die gesamte Matrix (z.B. beim Frame-Wechsel in Animation)."""
        self._rows = len(matrix)
        self._columns = len(matrix[0]) if matrix else 0
        self._matrix = [row[:] for row in matrix]
        self.update()

    def to_bitmap(self) -> bytes:
        """Konvertiert die Matrix in Column-Encoded Bitmap-Daten.

        Gleiches Format wie image_to_bitmap() in converter.py:
        Pro Spalte: ceil(rows/8) Bytes, MSB = oberste Zeile der Gruppe.
        """
        bytes_per_column = (self._rows + 7) // 8
        result = bytearray()

        for col in range(self._columns):
            for byte_group in range(bytes_per_column):
                start_row = byte_group * 8
                bits_in_group = min(8, self._rows - start_row)
                byte_val = 0
                for bit in range(bits_in_group):
                    row = start_row + bit
                    if self._matrix[row][col]:
                        byte_val |= (1 << (7 - bit))
                result.append(byte_val)

        return bytes(result)

    def from_bitmap(self, bitmap: bytes) -> None:
        """Lädt Matrix aus Column-Encoded Bitmap-Daten.

        Gleiche Dekodierung wie LedPreview.set_bitmap().
        """
        bytes_per_col = (self._rows + 7) // 8
        # Matrix zurücksetzen
        self._matrix = [[False] * self._columns for _ in range(self._rows)]

        for col in range(self._columns):
            for byte_group in range(bytes_per_col):
                byte_idx = col * bytes_per_col + byte_group
                if byte_idx >= len(bitmap):
                    self.update()
                    return
                byte_val = bitmap[byte_idx]
                start_row = byte_group * 8
                bits = min(8, self._rows - start_row)
                for bit in range(bits):
                    row = start_row + bit
                    if row < self._rows:
                        self._matrix[row][col] = bool(byte_val & (1 << (7 - bit)))

        self.update()

    # --- Maus-Events ---

    def _cell_size(self) -> tuple[float, float]:
        """Berechnet die Pixel-Größe einer einzelnen Zelle."""
        if self._rows == 0 or self._columns == 0:
            return 0.0, 0.0
        return self.width() / self._columns, self.height() / self._rows

    def _cell_at(self, x: float, y: float) -> tuple[int, int] | None:
        """Ermittelt die Zelle (row, col) an der gegebenen Pixel-Position."""
        cell_w, cell_h = self._cell_size()
        if cell_w <= 0 or cell_h <= 0:
            return None
        col = int(x / cell_w)
        row = int(y / cell_h)
        if 0 <= row < self._rows and 0 <= col < self._columns:
            return row, col
        return None

    def _apply_tool(self, row: int, col: int) -> None:
        """Wendet das aktive Werkzeug auf eine Zelle an."""
        if self._tool == TOOL_DRAW:
            self._matrix[row][col] = True
        elif self._tool == TOOL_ERASE:
            self._matrix[row][col] = False

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drawing = True
            cell = self._cell_at(event.position().x(), event.position().y())
            if cell:
                self._last_cell = cell
                self._apply_tool(cell[0], cell[1])
                self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._drawing:
            cell = self._cell_at(event.position().x(), event.position().y())
            if cell and cell != self._last_cell:
                self._last_cell = cell
                self._apply_tool(cell[0], cell[1])
                self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drawing:
            self._drawing = False
            self._last_cell = None
            self.grid_changed.emit()

    # --- Zeichnen ---

    def paintEvent(self, event) -> None:
        """Zeichnet das Pixel-Grid mit LEDs und Grid-Overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Hintergrund
        painter.fillRect(self.rect(), self.COLOR_BACKGROUND)

        if self._rows == 0 or self._columns == 0:
            painter.end()
            return

        cell_w, cell_h = self._cell_size()
        led_size = min(cell_w, cell_h) * 0.75
        radius = led_size / 2

        # LEDs zeichnen
        painter.setPen(Qt.PenStyle.NoPen)
        for row in range(self._rows):
            for col in range(self._columns):
                cx = col * cell_w + cell_w / 2
                cy = row * cell_h + cell_h / 2

                if self._matrix[row][col]:
                    painter.setBrush(QBrush(self.COLOR_LED_ON))
                else:
                    painter.setBrush(QBrush(self.COLOR_LED_OFF))

                painter.drawEllipse(QRectF(cx - radius, cy - radius, led_size, led_size))

        # Grid-Linien zeichnen
        grid_pen = QPen(self.COLOR_GRID)
        grid_pen.setWidthF(0.5)
        painter.setPen(grid_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Vertikale Linien
        for col in range(self._columns + 1):
            x = col * cell_w
            painter.drawLine(QRectF(x, 0, 0, 0).topLeft(),
                             QRectF(x, self._rows * cell_h, 0, 0).topLeft())

        # Horizontale Linien
        for row in range(self._rows + 1):
            y = row * cell_h
            painter.drawLine(QRectF(0, y, 0, 0).topLeft(),
                             QRectF(self._columns * cell_w, y, 0, 0).topLeft())

        painter.end()

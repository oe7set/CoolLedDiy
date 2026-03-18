"""
Hex-Dump Display Widget für den Debug-Tab.

Zeigt gesendete (TX) und empfangene (RX) BLE-Daten als formatierten
Hex-Dump mit Timestamp und Richtungs-Marker an.
"""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat
from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget


class HexViewer(QWidget):
    """Widget das BLE-Daten als Hex-Dump anzeigt.

    Format pro Eintrag:
      [HH:MM:SS.mmm] TX/RX | XX XX XX XX ... | ASCII
    """

    # Farben für TX/RX Unterscheidung
    COLOR_TX = QColor(100, 180, 255)   # Blau für gesendete Daten
    COLOR_RX = QColor(100, 255, 150)   # Grün für empfangene Daten
    COLOR_TIMESTAMP = QColor(180, 180, 180)  # Grau für Timestamp

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFont(QFont("Consolas", 9))
        self._text_edit.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: #d4d4d4; }"
        )
        layout.addWidget(self._text_edit)

    def add_tx(self, data: bytes) -> None:
        """Fügt gesendete Daten (TX) zum Log hinzu."""
        self._add_entry("TX", data, self.COLOR_TX)

    def add_rx(self, data: bytes) -> None:
        """Fügt empfangene Daten (RX) zum Log hinzu."""
        self._add_entry("RX", data, self.COLOR_RX)

    def _add_entry(self, direction: str, data: bytes, color: QColor) -> None:
        """Fügt einen Hex-Dump-Eintrag zum Log hinzu."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        hex_str = " ".join(f"{b:02X}" for b in data)

        # ASCII-Darstellung (nicht-druckbare Zeichen als Punkt)
        ascii_str = "".join(
            chr(b) if 32 <= b < 127 else "." for b in data
        )

        # Formatierter Eintrag
        line = f"[{timestamp}] {direction} | {hex_str} | {ascii_str}"

        # Farbig einfügen
        cursor = self._text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        fmt = QTextCharFormat()
        fmt.setForeground(color)
        cursor.insertText(line + "\n", fmt)

        # Auto-Scroll nach unten
        self._text_edit.setTextCursor(cursor)
        self._text_edit.ensureCursorVisible()

    def clear(self) -> None:
        """Löscht das gesamte Log."""
        self._text_edit.clear()

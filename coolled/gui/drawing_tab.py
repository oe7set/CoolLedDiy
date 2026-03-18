"""
Drawing Tab - Pixel-Editor zum Zeichnen auf einer virtuellen LED-Matrix.

Enthält:
- Interaktives Pixel-Grid (DrawingGrid)
- Werkzeuge: Zeichnen, Radieren, Löschen
- LED-Vorschau (LedPreview)
- Panel-Größe Einstellung
- Senden an das Panel
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from coolled.gui.widgets.drawing_grid import TOOL_DRAW, TOOL_ERASE, DrawingGrid
from coolled.gui.widgets.led_preview import LedPreview


class DrawingTab(QWidget):
    """Tab zum Zeichnen auf einer virtuellen LED-Matrix und Senden an das Panel."""

    # Signal mit den zu sendenden Bitmap-Daten
    send_drawing_requested = Signal(bytes)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Panel-Größe + Toolbar
        top_layout = QHBoxLayout()

        # Panel-Größe
        size_group = QGroupBox("Panel-Größe")
        size_layout = QHBoxLayout(size_group)
        size_layout.addWidget(QLabel("Zeilen:"))
        self._rows_spin = QSpinBox()
        self._rows_spin.setRange(8, 64)
        self._rows_spin.setValue(16)
        size_layout.addWidget(self._rows_spin)
        size_layout.addWidget(QLabel("Spalten:"))
        self._cols_spin = QSpinBox()
        self._cols_spin.setRange(8, 256)
        self._cols_spin.setValue(64)
        size_layout.addWidget(self._cols_spin)
        top_layout.addWidget(size_group)

        # Werkzeuge
        tool_group = QGroupBox("Werkzeuge")
        tool_layout = QHBoxLayout(tool_group)

        self._draw_btn = QPushButton("Zeichnen")
        self._draw_btn.setCheckable(True)
        self._draw_btn.setChecked(True)

        self._erase_btn = QPushButton("Radieren")
        self._erase_btn.setCheckable(True)

        # Gegenseitige Exklusivität
        self._tool_group = QButtonGroup(self)
        self._tool_group.addButton(self._draw_btn, TOOL_DRAW)
        self._tool_group.addButton(self._erase_btn, TOOL_ERASE)

        self._clear_btn = QPushButton("Löschen")

        tool_layout.addWidget(self._draw_btn)
        tool_layout.addWidget(self._erase_btn)
        tool_layout.addWidget(self._clear_btn)
        top_layout.addWidget(tool_group)

        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Zeichenfläche + Vorschau (Splitter)
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)

        # DrawingGrid (Hauptbereich)
        self._grid = DrawingGrid(16, 64)
        splitter.addWidget(self._grid)

        # LED-Vorschau
        preview_group = QGroupBox("LED-Vorschau")
        preview_layout = QVBoxLayout(preview_group)
        self._preview = LedPreview(16, 64)
        self._preview.setMaximumHeight(120)
        preview_layout.addWidget(self._preview)
        splitter.addWidget(preview_group)

        # Splitter-Proportionen: Grid groß, Vorschau klein
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        # Senden-Button
        self._send_btn = QPushButton("An Panel senden")
        self._send_btn.setMinimumHeight(36)
        layout.addWidget(self._send_btn)

    def _connect_signals(self) -> None:
        """Verdrahtet interne Signals."""
        # Werkzeug-Auswahl
        self._tool_group.idClicked.connect(self._grid.set_tool)

        # Löschen
        self._clear_btn.clicked.connect(self._grid.clear)

        # Grid-Änderung → Vorschau aktualisieren
        self._grid.grid_changed.connect(self._update_preview)

        # Panel-Größe ändern
        self._rows_spin.valueChanged.connect(self._on_size_changed)
        self._cols_spin.valueChanged.connect(self._on_size_changed)

        # Senden
        self._send_btn.clicked.connect(self._on_send)

    def _update_preview(self) -> None:
        """Aktualisiert die LED-Vorschau aus dem Grid."""
        bitmap = self._grid.to_bitmap()
        self._preview.set_bitmap(bitmap, self._grid.rows)

    def _on_size_changed(self) -> None:
        """Passt Grid und Vorschau an neue Panel-Größe an."""
        rows = self._rows_spin.value()
        cols = self._cols_spin.value()
        self._grid.set_size(rows, cols)
        self._preview.set_size(rows, cols)

    def _on_send(self) -> None:
        """Sendet die aktuelle Zeichnung als Bitmap."""
        bitmap = self._grid.to_bitmap()
        self.send_drawing_requested.emit(bitmap)

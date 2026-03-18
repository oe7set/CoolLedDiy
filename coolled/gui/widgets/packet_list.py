"""
Paket-Liste Widget für den Debug-Tab.

Zeigt alle TX/RX-Pakete in einer scrollbaren Tabelle mit Farb-Codierung,
Zeitstempel und Auto-Scroll. Unterstützt Filterung und Paket-Auswahl.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from coolled.models.packet_log import PacketLog
from coolled.protocol.constants import CMD_NAMES


# Hintergrundfarben für TX/RX Zeilen
COLOR_TX_BG = QColor(20, 40, 70)    # Dunkles Blau
COLOR_RX_BG = QColor(20, 60, 30)    # Dunkles Grün
COLOR_TX_FG = QColor(130, 200, 255)  # Helles Blau
COLOR_RX_FG = QColor(130, 255, 180)  # Helles Grün


class PacketListWidget(QWidget):
    """Paket-Liste mit Filterung und Farb-Codierung."""

    # Signal: Index des ausgewählten Pakets im PacketLog
    packet_selected = Signal(int)

    def __init__(self, packet_log: PacketLog, parent: QWidget | None = None):
        super().__init__(parent)
        self._packet_log = packet_log
        self._auto_scroll = True
        self._filtered_indices: list[int] | None = None  # None = kein Filter aktiv
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Filter-Toolbar
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Richtung:"))
        self._dir_combo = QComboBox()
        self._dir_combo.addItems(["Alle", "TX", "RX"])
        self._dir_combo.setFixedWidth(70)
        filter_layout.addWidget(self._dir_combo)

        filter_layout.addWidget(QLabel("Kommando:"))
        self._cmd_combo = QComboBox()
        self._cmd_combo.addItem("Alle", None)
        for cmd_byte, cmd_name in sorted(CMD_NAMES.items()):
            self._cmd_combo.addItem(f"0x{cmd_byte:02X} {cmd_name}", cmd_byte)
        self._cmd_combo.setFixedWidth(180)
        filter_layout.addWidget(self._cmd_combo)

        filter_layout.addWidget(QLabel("Hex:"))
        self._hex_search = QLineEdit()
        self._hex_search.setPlaceholderText("z.B. FF 00")
        self._hex_search.setFixedWidth(100)
        self._hex_search.setFont(QFont("Consolas", 9))
        filter_layout.addWidget(self._hex_search)

        filter_layout.addWidget(QLabel("Text:"))
        self._text_search = QLineEdit()
        self._text_search.setPlaceholderText("Suche in Summary...")
        self._text_search.setFixedWidth(140)
        filter_layout.addWidget(self._text_search)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Tabelle
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["#", "Zeit", "Dir", "Länge", "Kommando", "Summary"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setFont(QFont("Consolas", 9))
        self._table.setStyleSheet(
            "QTableWidget { background-color: #1e1e1e; color: #d4d4d4; gridline-color: #333; }"
            "QHeaderView::section { background-color: #2d2d2d; color: #d4d4d4; padding: 4px; }"
        )
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

    def _connect_signals(self) -> None:
        # PacketLog → neue Zeile hinzufügen
        self._packet_log.packet_added.connect(self._on_packet_added)
        self._packet_log.log_cleared.connect(self._on_log_cleared)

        # Tabellenauswahl → Signal
        self._table.currentCellChanged.connect(self._on_cell_changed)

        # Filter-Änderungen
        self._dir_combo.currentTextChanged.connect(self._apply_filter)
        self._cmd_combo.currentIndexChanged.connect(self._apply_filter)
        self._hex_search.textChanged.connect(self._apply_filter)
        self._text_search.textChanged.connect(self._apply_filter)

        # Auto-Scroll: deaktivieren wenn der User hoch scrollt
        scrollbar = self._table.verticalScrollBar()
        scrollbar.valueChanged.connect(self._check_auto_scroll)

    def _on_packet_added(self, index: int) -> None:
        """Wird aufgerufen wenn ein neues Paket geloggt wurde."""
        # Prüfen ob das Paket den aktuellen Filter passiert
        if self._is_filter_active():
            entry = self._packet_log.get(index)
            if entry and not self._matches_filter(entry):
                return

        self._add_table_row(index)

        # Auto-Scroll
        if self._auto_scroll:
            self._table.scrollToBottom()

    def _on_log_cleared(self) -> None:
        """Log wurde gelöscht."""
        self._table.setRowCount(0)
        self._filtered_indices = None

    def _on_cell_changed(self, row: int, _col: int, _prev_row: int, _prev_col: int) -> None:
        """Zeile in der Tabelle ausgewählt."""
        if row < 0:
            return
        # Index aus der versteckten ersten Spalte lesen
        item = self._table.item(row, 0)
        if item:
            packet_index = int(item.text())
            self.packet_selected.emit(packet_index)

    def _check_auto_scroll(self, value: int) -> None:
        """Deaktiviert Auto-Scroll wenn der User nach oben scrollt."""
        scrollbar = self._table.verticalScrollBar()
        self._auto_scroll = value >= scrollbar.maximum() - 5

    def _add_table_row(self, packet_index: int) -> None:
        """Fügt eine Zeile für ein Paket zur Tabelle hinzu."""
        entry = self._packet_log.get(packet_index)
        if not entry:
            return

        row = self._table.rowCount()
        self._table.insertRow(row)

        # Zellen erstellen
        items = [
            QTableWidgetItem(str(entry.index)),
            QTableWidgetItem(entry.timestamp.strftime("%H:%M:%S.%f")[:-3]),
            QTableWidgetItem(entry.direction),
            QTableWidgetItem(str(len(entry.raw_data))),
            QTableWidgetItem(entry.command_name),
            QTableWidgetItem(entry.summary),
        ]

        # Farben setzen
        bg = COLOR_TX_BG if entry.direction == "TX" else COLOR_RX_BG
        fg = COLOR_TX_FG if entry.direction == "TX" else COLOR_RX_FG

        for col, item in enumerate(items):
            item.setBackground(bg)
            item.setForeground(fg)
            self._table.setItem(row, col, item)

        self._table.setRowHeight(row, 22)

    def _is_filter_active(self) -> bool:
        """Prüft ob ein Filter aktiv ist."""
        return (
            self._dir_combo.currentText() != "Alle"
            or self._cmd_combo.currentData() is not None
            or self._hex_search.text().strip() != ""
            or self._text_search.text().strip() != ""
        )

    def _matches_filter(self, entry) -> bool:
        """Prüft ob ein Eintrag den aktuellen Filter erfüllt."""
        # Richtung
        dir_filter = self._dir_combo.currentText()
        if dir_filter != "Alle" and entry.direction != dir_filter:
            return False

        # Kommando
        cmd_filter = self._cmd_combo.currentData()
        if cmd_filter is not None and entry.command != cmd_filter:
            return False

        # Hex-Suche
        hex_text = self._hex_search.text().strip()
        if hex_text:
            try:
                search_bytes = bytes.fromhex(hex_text.replace(" ", ""))
                if search_bytes not in entry.raw_data:
                    return False
            except ValueError:
                pass

        # Text-Suche
        text = self._text_search.text().strip().lower()
        if text:
            if text not in entry.summary.lower() and text not in entry.command_name.lower():
                return False

        return True

    def _apply_filter(self) -> None:
        """Wendet den aktuellen Filter auf die Tabelle an."""
        self._table.setRowCount(0)

        direction = self._dir_combo.currentText()
        direction = None if direction == "Alle" else direction
        command = self._cmd_combo.currentData()
        hex_search = self._hex_search.text().strip() or None
        text_search = self._text_search.text().strip() or None

        entries = self._packet_log.filter_entries(direction, command, hex_search, text_search)
        for entry in entries:
            self._add_table_row(entry.index)

    def selected_packet_index(self) -> int | None:
        """Gibt den PacketLog-Index des aktuell ausgewählten Pakets zurück."""
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return int(item.text()) if item else None

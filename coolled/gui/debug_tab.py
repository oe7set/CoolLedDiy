"""
Debug Tab - Protokoll-Analyse-Werkbank für Reverse Engineering.

Enthält:
- Paket-Liste mit Filterung und Farb-Codierung (TX/RX)
- Paket-Dissector (Feld-für-Feld-Analyse)
- Raw-Hex-Sender und Paket-Builder
- Replay-Funktion (Paket erneut senden, Sequenz abspielen)
- Echtzeit-Statistiken (TX/RX Pakete, Bytes, Datenrate)
- Export (CSV, Hex-Dump)
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from coolled.gui.widgets.packet_dissector import PacketDissectorWidget
from coolled.gui.widgets.packet_list import PacketListWidget
from coolled.gui.widgets.stats_panel import StatsPanel
from coolled.models.packet_log import PacketLog
from coolled.protocol.constants import CMD_NAMES
from coolled.protocol.framing import frame_packet


class DebugTab(QWidget):
    """Protokoll-Analyse-Werkbank mit Paketliste, Dissector, Builder, Replay und Statistiken."""

    # Signal zum Senden von Raw-Daten (Interface bleibt kompatibel mit MainWindow)
    send_raw_requested = Signal(bytes)

    def __init__(self, packet_log: PacketLog, parent: QWidget | None = None):
        super().__init__(parent)
        self._packet_log = packet_log
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)

        # Haupt-Splitter: Links (Paketliste + Dissector + Tools) | Rechts (Stats)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Linke Seite: Vertikaler Splitter
        left_splitter = QSplitter(Qt.Orientation.Vertical)

        # Oben: Paket-Liste mit Toolbar
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar über der Paketliste
        toolbar = QHBoxLayout()
        self._clear_btn = QPushButton("Log löschen")
        toolbar.addWidget(self._clear_btn)
        self._export_btn = QPushButton("Exportieren...")
        toolbar.addWidget(self._export_btn)
        toolbar.addStretch()
        list_layout.addLayout(toolbar)

        # Paket-Liste
        self._packet_list = PacketListWidget(self._packet_log)
        list_layout.addWidget(self._packet_list)
        left_splitter.addWidget(list_container)

        # Mitte: Paket-Dissector
        self._dissector = PacketDissectorWidget()
        left_splitter.addWidget(self._dissector)

        # Unten: Tools (Tabs: Raw Senden | Paket-Builder | Replay)
        tools_tabs = QTabWidget()
        tools_tabs.setMaximumHeight(220)

        # Tab 1: Raw Senden
        raw_tab = QWidget()
        raw_layout = QVBoxLayout(raw_tab)
        raw_input_layout = QHBoxLayout()
        self._hex_input = QLineEdit()
        self._hex_input.setFont(QFont("Consolas", 10))
        self._hex_input.setPlaceholderText("Hex-Bytes eingeben, z.B.: 01 00 02 08 04 03")
        raw_input_layout.addWidget(self._hex_input)
        self._send_raw_btn = QPushButton("Senden")
        raw_input_layout.addWidget(self._send_raw_btn)
        raw_layout.addLayout(raw_input_layout)
        hint = QLabel("Hex-Bytes mit Leerzeichen getrennt. Wird direkt ohne Framing gesendet.")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        raw_layout.addWidget(hint)
        raw_layout.addStretch()
        tools_tabs.addTab(raw_tab, "Raw Senden")

        # Tab 2: Paket-Builder
        builder_tab = QWidget()
        builder_layout = QVBoxLayout(builder_tab)

        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(QLabel("Kommando:"))
        self._builder_cmd = QComboBox()
        for cmd_byte, cmd_name in sorted(CMD_NAMES.items()):
            self._builder_cmd.addItem(f"0x{cmd_byte:02X} {cmd_name}", cmd_byte)
        cmd_layout.addWidget(self._builder_cmd)

        cmd_layout.addWidget(QLabel("Payload (Hex):"))
        self._builder_payload = QLineEdit()
        self._builder_payload.setFont(QFont("Consolas", 10))
        self._builder_payload.setPlaceholderText("Optionale Payload-Daten, z.B.: 04")
        cmd_layout.addWidget(self._builder_payload)
        builder_layout.addLayout(cmd_layout)

        # Vorschau + Senden
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("Frame:"))
        self._builder_preview = QLineEdit()
        self._builder_preview.setFont(QFont("Consolas", 9))
        self._builder_preview.setReadOnly(True)
        self._builder_preview.setStyleSheet("background-color: #2d2d2d; color: #aaa;")
        preview_layout.addWidget(self._builder_preview)
        self._builder_send_btn = QPushButton("Senden")
        preview_layout.addWidget(self._builder_send_btn)
        builder_layout.addLayout(preview_layout)
        builder_layout.addStretch()
        tools_tabs.addTab(builder_tab, "Paket-Builder")

        # Tab 3: Replay
        replay_tab = QWidget()
        replay_layout = QVBoxLayout(replay_tab)

        single_layout = QHBoxLayout()
        self._resend_btn = QPushButton("Ausgewähltes Paket erneut senden")
        single_layout.addWidget(self._resend_btn)
        single_layout.addStretch()
        replay_layout.addLayout(single_layout)

        seq_layout = QHBoxLayout()
        seq_layout.addWidget(QLabel("Sequenz-Delay (ms):"))
        self._replay_delay = QSpinBox()
        self._replay_delay.setRange(10, 5000)
        self._replay_delay.setValue(100)
        seq_layout.addWidget(self._replay_delay)
        self._replay_all_btn = QPushButton("Alle TX-Pakete abspielen")
        seq_layout.addWidget(self._replay_all_btn)
        seq_layout.addStretch()
        replay_layout.addLayout(seq_layout)

        self._replay_status = QLabel("")
        self._replay_status.setStyleSheet("color: gray; font-size: 11px;")
        replay_layout.addWidget(self._replay_status)
        replay_layout.addStretch()
        tools_tabs.addTab(replay_tab, "Replay")

        left_splitter.addWidget(tools_tabs)

        # Splitter-Proportionen: Liste 3 : Dissector 2 : Tools 1
        left_splitter.setStretchFactor(0, 3)
        left_splitter.setStretchFactor(1, 2)
        left_splitter.setStretchFactor(2, 1)

        main_splitter.addWidget(left_splitter)

        # Rechte Seite: Statistiken
        self._stats_panel = StatsPanel(self._packet_log)
        self._stats_panel.setMinimumWidth(180)
        self._stats_panel.setMaximumWidth(250)
        main_splitter.addWidget(self._stats_panel)

        main_splitter.setStretchFactor(0, 4)
        main_splitter.setStretchFactor(1, 1)

        layout.addWidget(main_splitter)

    def _connect_signals(self) -> None:
        # Paket-Auswahl → Dissector
        self._packet_list.packet_selected.connect(self._on_packet_selected)

        # Log löschen
        self._clear_btn.clicked.connect(self._packet_log.clear)

        # Export
        self._export_btn.clicked.connect(self._on_export)

        # Raw Senden
        self._send_raw_btn.clicked.connect(self._on_send_raw)
        self._hex_input.returnPressed.connect(self._on_send_raw)

        # Paket-Builder: Vorschau aktualisieren bei Änderung
        self._builder_cmd.currentIndexChanged.connect(self._update_builder_preview)
        self._builder_payload.textChanged.connect(self._update_builder_preview)
        self._builder_send_btn.clicked.connect(self._on_builder_send)
        self._update_builder_preview()

        # Replay
        self._resend_btn.clicked.connect(self._on_resend_selected)
        self._replay_all_btn.clicked.connect(self._on_replay_all)

    # --- Interface für MainWindow (Kompatibilität) ---

    def log_tx(self, data: bytes) -> None:
        """Loggt gesendete Daten — delegiert an PacketLog."""
        self._packet_log.add_tx(data)

    def log_rx(self, data: bytes) -> None:
        """Loggt empfangene Daten — delegiert an PacketLog."""
        self._packet_log.add_rx(data)

    # --- Callbacks ---

    def _on_packet_selected(self, index: int) -> None:
        """Paket ausgewählt → im Dissector anzeigen."""
        entry = self._packet_log.get(index)
        if entry:
            self._dissector.set_packet(entry)

    def _on_export(self) -> None:
        """Öffnet Export-Dialog."""
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "Paket-Log exportieren", "packet_log",
            "CSV (*.csv);;Hex-Dump (*.txt)"
        )
        if not path:
            return

        if "csv" in selected_filter.lower():
            if not path.endswith(".csv"):
                path += ".csv"
            self._packet_log.export_csv(path)
        else:
            if not path.endswith(".txt"):
                path += ".txt"
            self._packet_log.export_hex_dump(path)

    def _on_send_raw(self) -> None:
        """Parst Hex-Input und sendet als Raw-Daten."""
        hex_text = self._hex_input.text().strip()
        if not hex_text:
            return
        try:
            hex_clean = hex_text.replace(" ", "").replace("0x", "").replace(",", "")
            data = bytes.fromhex(hex_clean)
            self.send_raw_requested.emit(data)
            self._hex_input.clear()
        except ValueError:
            pass  # Ungültiges Hex ignorieren

    def _update_builder_preview(self) -> None:
        """Aktualisiert die Frame-Vorschau im Paket-Builder."""
        cmd_byte = self._builder_cmd.currentData()
        if cmd_byte is None:
            self._builder_preview.clear()
            return

        payload = bytes([cmd_byte])

        # Optionale Payload-Daten
        payload_hex = self._builder_payload.text().strip()
        if payload_hex:
            try:
                extra = bytes.fromhex(payload_hex.replace(" ", "").replace("0x", ""))
                payload += extra
            except ValueError:
                pass

        framed = frame_packet(payload)
        self._builder_preview.setText(framed.hex(" "))

    def _on_builder_send(self) -> None:
        """Sendet das im Paket-Builder zusammengestellte Paket."""
        cmd_byte = self._builder_cmd.currentData()
        if cmd_byte is None:
            return

        payload = bytes([cmd_byte])
        payload_hex = self._builder_payload.text().strip()
        if payload_hex:
            try:
                extra = bytes.fromhex(payload_hex.replace(" ", "").replace("0x", ""))
                payload += extra
            except ValueError:
                return

        framed = frame_packet(payload)
        self.send_raw_requested.emit(framed)

    def _on_resend_selected(self) -> None:
        """Sendet das ausgewählte Paket erneut."""
        index = self._packet_list.selected_packet_index()
        if index is None:
            self._replay_status.setText("Kein Paket ausgewählt")
            return
        entry = self._packet_log.get(index)
        if entry:
            self.send_raw_requested.emit(entry.raw_data)
            self._replay_status.setText(f"Paket #{entry.index} erneut gesendet")

    def _on_replay_all(self) -> None:
        """Spielt alle TX-Pakete mit konfiguriertem Delay ab."""
        tx_entries = [e for e in self._packet_log.all_entries() if e.direction == "TX"]
        if not tx_entries:
            self._replay_status.setText("Keine TX-Pakete vorhanden")
            return

        delay = self._replay_delay.value()
        self._replay_queue = list(tx_entries)
        self._replay_idx = 0
        self._replay_status.setText(f"Replay: 0/{len(tx_entries)} Pakete...")

        # Timer für verzögertes Abspielen
        self._replay_timer = QTimer(self)
        self._replay_timer.timeout.connect(self._replay_next)
        self._replay_timer.start(delay)

    def _replay_next(self) -> None:
        """Sendet das nächste Paket in der Replay-Sequenz."""
        if self._replay_idx >= len(self._replay_queue):
            self._replay_timer.stop()
            self._replay_status.setText(
                f"Replay abgeschlossen: {len(self._replay_queue)} Pakete gesendet"
            )
            return

        entry = self._replay_queue[self._replay_idx]
        self.send_raw_requested.emit(entry.raw_data)
        self._replay_idx += 1
        self._replay_status.setText(
            f"Replay: {self._replay_idx}/{len(self._replay_queue)} Pakete..."
        )

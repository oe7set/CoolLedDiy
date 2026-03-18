"""
Debug Tab - Protokoll-Analyse und Raw-Hex-Kommunikation.

Enthält:
- TX/RX Hex-Log (alle BLE-Kommunikation)
- Verbindungsstatus-Anzeige
- Raw-Command-Builder (manuelles Hex senden)
- Protokoll-Decoder (Frame analysieren)
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from coolled.gui.widgets.hex_viewer import HexViewer
from coolled.protocol.framing import unframe_packet


class DebugTab(QWidget):
    """Debug-Panel für Protokoll-Analyse und Raw-Kommunikation."""

    # Signal zum Senden von Raw-Hex-Daten
    send_raw_requested = Signal(bytes)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Splitter: Hex-Log oben, Tools unten
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)

        # Hex-Log
        log_group = QGroupBox("BLE Kommunikations-Log")
        log_layout = QVBoxLayout(log_group)
        self._hex_viewer = HexViewer()
        log_layout.addWidget(self._hex_viewer)

        # Clear-Button
        clear_btn = QPushButton("Log löschen")
        clear_btn.clicked.connect(self._hex_viewer.clear)
        log_layout.addWidget(clear_btn)
        splitter.addWidget(log_group)

        # Unterer Bereich: Raw-Sender + Decoder
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)

        # Raw-Command-Builder
        raw_group = QGroupBox("Raw-Hex senden")
        raw_layout = QVBoxLayout(raw_group)

        input_layout = QHBoxLayout()
        self._hex_input = QLineEdit()
        self._hex_input.setFont(QFont("Consolas", 10))
        self._hex_input.setPlaceholderText("Hex-Bytes eingeben, z.B.: 01 00 02 08 04 03")
        input_layout.addWidget(self._hex_input)
        self._send_raw_btn = QPushButton("Senden")
        self._send_raw_btn.clicked.connect(self._on_send_raw)
        input_layout.addWidget(self._send_raw_btn)
        raw_layout.addLayout(input_layout)

        # Hinweis
        hint = QLabel("Hex-Bytes mit Leerzeichen getrennt. Wird direkt ohne Framing gesendet.")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        raw_layout.addWidget(hint)

        bottom_layout.addWidget(raw_group)

        # Protokoll-Decoder
        decoder_group = QGroupBox("Protokoll-Decoder")
        decoder_layout = QVBoxLayout(decoder_group)

        decode_input_layout = QHBoxLayout()
        self._decode_input = QLineEdit()
        self._decode_input.setFont(QFont("Consolas", 10))
        self._decode_input.setPlaceholderText("Frame-Hex zum Decodieren, z.B.: 01 00 02 08 04 03")
        decode_input_layout.addWidget(self._decode_input)
        self._decode_btn = QPushButton("Decodieren")
        self._decode_btn.clicked.connect(self._on_decode)
        decode_input_layout.addWidget(self._decode_btn)
        decoder_layout.addLayout(decode_input_layout)

        self._decode_output = QTextEdit()
        self._decode_output.setReadOnly(True)
        self._decode_output.setFont(QFont("Consolas", 9))
        self._decode_output.setMaximumHeight(150)
        self._decode_output.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: #d4d4d4; }"
        )
        decoder_layout.addWidget(self._decode_output)

        bottom_layout.addWidget(decoder_group)
        splitter.addWidget(bottom)

        layout.addWidget(splitter)

    def log_tx(self, data: bytes) -> None:
        """Loggt gesendete Daten im Hex-Viewer."""
        self._hex_viewer.add_tx(data)

    def log_rx(self, data: bytes) -> None:
        """Loggt empfangene Daten im Hex-Viewer."""
        self._hex_viewer.add_rx(data)

    def _on_send_raw(self) -> None:
        """Parst Hex-Input und sendet als Raw-Daten."""
        hex_text = self._hex_input.text().strip()
        if not hex_text:
            return

        try:
            # Hex-String zu Bytes konvertieren
            hex_clean = hex_text.replace(" ", "").replace("0x", "").replace(",", "")
            data = bytes.fromhex(hex_clean)
            self.send_raw_requested.emit(data)
            self._hex_input.clear()
        except ValueError as e:
            self._decode_output.setPlainText(f"Ungültiges Hex-Format: {e}")

    def _on_decode(self) -> None:
        """Decodiert ein Frame-Paket und zeigt die Analyse an."""
        hex_text = self._decode_input.text().strip()
        if not hex_text:
            return

        try:
            hex_clean = hex_text.replace(" ", "").replace("0x", "").replace(",", "")
            data = bytes.fromhex(hex_clean)
        except ValueError as e:
            self._decode_output.setPlainText(f"Ungültiges Hex-Format: {e}")
            return

        lines = []
        lines.append(f"Raw ({len(data)} Bytes): {data.hex(' ')}")
        lines.append("")

        # Frame-Check
        if len(data) >= 2 and data[0] == 0x01 and data[-1] == 0x03:
            lines.append("Frame erkannt: START=0x01, END=0x03")

            payload = unframe_packet(data)
            if payload is not None:
                lines.append(f"Payload ({len(payload)} Bytes): {payload.hex(' ')}")

                # Kommando identifizieren
                if len(payload) >= 1:
                    cmd = payload[0]
                    cmd_names = {
                        0x01: "MUSIC", 0x02: "TEXT", 0x03: "DRAW",
                        0x05: "ICON", 0x06: "MODE", 0x07: "SPEED",
                        0x08: "BRIGHTNESS", 0x09: "SWITCH", 0x0A: "BEGIN_TRANSFER",
                    }
                    cmd_name = cmd_names.get(cmd, f"UNKNOWN(0x{cmd:02X})")
                    lines.append(f"Kommando: 0x{cmd:02X} ({cmd_name})")

                    if len(payload) > 1:
                        lines.append(f"Daten: {payload[1:].hex(' ')}")
            else:
                lines.append("Frame-Dekodierung fehlgeschlagen!")
        else:
            lines.append("Kein gültiges Frame (erwartet: 0x01...0x03)")

        self._decode_output.setPlainText("\n".join(lines))

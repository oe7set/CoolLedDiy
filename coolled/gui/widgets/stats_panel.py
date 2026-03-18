"""
Statistik-Panel Widget für den Debug-Tab.

Zeigt Echtzeit-Statistiken über die BLE-Kommunikation:
TX/RX Pakete/Bytes, Datenrate, Sitzungsdauer, Kommando-Verteilung.
"""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from coolled.models.packet_log import PacketLog


class StatsPanel(QWidget):
    """Echtzeit-Statistiken über die BLE-Kommunikation."""

    def __init__(self, packet_log: PacketLog, parent: QWidget | None = None):
        super().__init__(parent)
        self._packet_log = packet_log
        self._setup_ui()

        # Auto-Update alle 1 Sekunde
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_stats)
        self._timer.start(1000)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Statistiken")
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #aaa;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 0)

        mono = QFont("Consolas", 9)

        self._tx_count = QLabel("0")
        self._tx_count.setFont(mono)
        form.addRow("TX Pakete:", self._tx_count)

        self._rx_count = QLabel("0")
        self._rx_count.setFont(mono)
        form.addRow("RX Pakete:", self._rx_count)

        self._tx_bytes = QLabel("0 B")
        self._tx_bytes.setFont(mono)
        form.addRow("TX Bytes:", self._tx_bytes)

        self._rx_bytes = QLabel("0 B")
        self._rx_bytes.setFont(mono)
        form.addRow("RX Bytes:", self._rx_bytes)

        self._data_rate = QLabel("0 B/s")
        self._data_rate.setFont(mono)
        form.addRow("Datenrate:", self._data_rate)

        self._duration = QLabel("00:00:00")
        self._duration.setFont(mono)
        form.addRow("Sitzung:", self._duration)

        layout.addLayout(form)

        # Kommando-Verteilung
        self._cmd_label = QLabel("Kommando-Verteilung")
        self._cmd_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._cmd_label.setStyleSheet("color: #aaa; margin-top: 8px;")
        layout.addWidget(self._cmd_label)

        self._cmd_dist = QLabel("")
        self._cmd_dist.setFont(mono)
        self._cmd_dist.setWordWrap(True)
        layout.addWidget(self._cmd_dist)

        layout.addStretch()

    def _format_bytes(self, n: int) -> str:
        """Formatiert Bytes in lesbare Einheit."""
        if n < 1024:
            return f"{n} B"
        elif n < 1024 * 1024:
            return f"{n / 1024:.1f} KB"
        return f"{n / (1024 * 1024):.1f} MB"

    def _format_duration(self, seconds: float) -> str:
        """Formatiert Sekunden in HH:MM:SS."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _update_stats(self) -> None:
        """Aktualisiert alle Statistik-Labels."""
        stats = self._packet_log.stats

        self._tx_count.setText(str(stats["tx_count"]))
        self._rx_count.setText(str(stats["rx_count"]))
        self._tx_bytes.setText(self._format_bytes(stats["tx_bytes"]))
        self._rx_bytes.setText(self._format_bytes(stats["rx_bytes"]))
        self._data_rate.setText(f"{stats['data_rate']:.1f} B/s")
        self._duration.setText(self._format_duration(stats["duration"]))

        # Kommando-Verteilung
        cmd_dist = stats["command_distribution"]
        if cmd_dist:
            lines = [f"  {name}: {count}" for name, count in
                     sorted(cmd_dist.items(), key=lambda x: -x[1])]
            self._cmd_dist.setText("\n".join(lines))
        else:
            self._cmd_dist.setText("  (keine Daten)")

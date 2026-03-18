"""
BLE Scanner Tab - Sucht und zeigt CoolLed BLE-Geräte an.

Enthält:
- Scan-Button zum Starten/Stoppen des BLE-Scans
- Tabelle mit gefundenen Geräten (Name, MAC, RSSI, Rows, Cols, Type, FW)
- Connect-Button zum Verbinden mit ausgewähltem Gerät
"""

import asyncio

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot

from coolled.ble.scanner import BleScanner, DiscoveredDevice


class ScannerTab(QWidget):
    """Tab zum Scannen und Verbinden mit CoolLed BLE-Geräten."""

    # Signal wenn ein Gerät zum Verbinden ausgewählt wurde
    connect_requested = Signal(object)  # DiscoveredDevice

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._scanner = BleScanner()
        self._devices: list[DiscoveredDevice] = []
        self._scanning = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Scan-Steuerung
        scan_group = QGroupBox("BLE Scanner")
        scan_layout = QHBoxLayout(scan_group)

        self._scan_btn = QPushButton("Scan starten")
        self._scan_btn.clicked.connect(self._on_scan_clicked)
        scan_layout.addWidget(self._scan_btn)

        scan_layout.addWidget(QLabel("Timeout (s):"))
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1, 30)
        self._timeout_spin.setValue(5)
        scan_layout.addWidget(self._timeout_spin)

        self._status_label = QLabel("Bereit")
        scan_layout.addWidget(self._status_label)
        scan_layout.addStretch()

        layout.addWidget(scan_group)

        # Geräte-Tabelle
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Name", "MAC-Adresse", "RSSI", "Zeilen", "Spalten", "Farb-Typ", "FW-Version"
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table)

        # Connect-Button
        btn_layout = QHBoxLayout()
        self._connect_btn = QPushButton("Verbinden")
        self._connect_btn.setEnabled(False)
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        btn_layout.addStretch()
        btn_layout.addWidget(self._connect_btn)
        layout.addLayout(btn_layout)

        # Tabellen-Selektion aktiviert Connect-Button
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

    @asyncSlot()
    async def _on_scan_clicked(self) -> None:
        """Startet oder stoppt den BLE-Scan."""
        if self._scanning:
            return

        self._scanning = True
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("Scanne...")
        self._status_label.setText("Suche nach Geräten...")
        self._table.setRowCount(0)

        try:
            timeout = self._timeout_spin.value()
            self._devices = await self._scanner.scan(timeout=timeout)
            self._update_table()
            self._status_label.setText(f"{len(self._devices)} Gerät(e) gefunden")
        except Exception as e:
            self._status_label.setText(f"Fehler: {e}")
        finally:
            self._scanning = False
            self._scan_btn.setEnabled(True)
            self._scan_btn.setText("Scan starten")

    def _update_table(self) -> None:
        """Aktualisiert die Tabelle mit den gefundenen Geräten."""
        self._table.setRowCount(len(self._devices))

        for row, device in enumerate(self._devices):
            self._table.setItem(row, 0, QTableWidgetItem(device.name))
            self._table.setItem(row, 1, QTableWidgetItem(device.address))
            self._table.setItem(row, 2, QTableWidgetItem(str(device.rssi)))

            if device.scan_info:
                info = device.scan_info
                self._table.setItem(row, 3, QTableWidgetItem(str(info.rows)))
                self._table.setItem(row, 4, QTableWidgetItem(str(info.columns)))
                self._table.setItem(row, 5, QTableWidgetItem(info.color_type_name))
                self._table.setItem(row, 6, QTableWidgetItem(str(info.fw_version)))
            else:
                for col in range(3, 7):
                    self._table.setItem(row, col, QTableWidgetItem("?"))

    def _on_selection_changed(self) -> None:
        """Aktiviert/deaktiviert den Connect-Button je nach Selektion."""
        self._connect_btn.setEnabled(len(self._table.selectedItems()) > 0)

    def _on_connect_clicked(self) -> None:
        """Sendet Signal mit dem ausgewählten Gerät."""
        row = self._table.currentRow()
        if 0 <= row < len(self._devices):
            self.connect_requested.emit(self._devices[row])

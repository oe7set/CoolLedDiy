"""
Hauptfenster der CoolLedDiy Anwendung.

Enthält:
- QTabWidget mit 5 Tabs (Scanner, Text, Bild, Controls, Debug)
- Status-Bar mit Verbindungsstatus
- Zentrale Verdrahtung aller Signals zwischen GUI und BLE-Layer
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QWidget,
)
from qasync import asyncSlot

from coolled.ble.connection import BleConnection
from coolled.ble.scanner import DiscoveredDevice
from coolled.ble.transport import BleTransport
from coolled.fonts.font_reader import FontReader
from coolled.gui.control_tab import ControlTab
from coolled.gui.debug_tab import DebugTab
from coolled.gui.image_tab import ImageTab
from coolled.gui.scanner_tab import ScannerTab
from coolled.gui.text_tab import TextTab
from coolled.protocol.commands import (
    cmd_begin_transfer,
    cmd_brightness,
    cmd_draw,
    cmd_mode,
    cmd_raw,
    cmd_speed,
    cmd_switch,
)
from coolled.protocol.text_encoding import encode_text_packets

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Hauptfenster mit Tab-Widget und Verbindungsverwaltung."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CoolLedDiy - LED Matrix Controller")
        self.setMinimumSize(800, 600)

        # BLE-Layer
        self._connection = BleConnection(self)
        self._transport = BleTransport(self._connection, self)
        self._font_reader = FontReader()

        # UI aufbauen
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Erstellt das Tab-Widget und die Status-Bar."""
        # Tab-Widget als zentrales Widget
        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        # Tabs erstellen
        self._scanner_tab = ScannerTab()
        self._text_tab = TextTab(self._font_reader)
        self._image_tab = ImageTab()
        self._control_tab = ControlTab()
        self._debug_tab = DebugTab()

        self._tabs.addTab(self._scanner_tab, "Scanner")
        self._tabs.addTab(self._text_tab, "Text")
        self._tabs.addTab(self._image_tab, "Bild")
        self._tabs.addTab(self._control_tab, "Controls")
        self._tabs.addTab(self._debug_tab, "Debug")

        # Status-Bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._connection_label = QLabel("Nicht verbunden")
        self._status_bar.addPermanentWidget(self._connection_label)

    def _connect_signals(self) -> None:
        """Verdrahtet alle Signals zwischen GUI und BLE-Layer."""
        # Scanner → Connect
        self._scanner_tab.connect_requested.connect(self._on_connect_requested)

        # Connection Status
        self._connection.connected.connect(self._on_connected)
        self._connection.disconnected.connect(self._on_disconnected)
        self._connection.connection_error.connect(self._on_connection_error)

        # BLE-Daten → Debug-Log
        self._transport.data_sent.connect(self._debug_tab.log_tx)
        self._connection.notify_received.connect(self._debug_tab.log_rx)

        # Text senden
        self._text_tab.send_text_requested.connect(self._on_send_text)

        # Bild senden
        self._image_tab.send_image_requested.connect(self._on_send_image)

        # Controls
        self._control_tab.switch_requested.connect(self._on_switch)
        self._control_tab.brightness_requested.connect(self._on_brightness)
        self._control_tab.speed_requested.connect(self._on_speed)
        self._control_tab.mode_requested.connect(self._on_mode)

        # Debug Raw-Send
        self._debug_tab.send_raw_requested.connect(self._on_send_raw)

    # --- Verbindungs-Handling ---

    @asyncSlot(object)
    async def _on_connect_requested(self, device: DiscoveredDevice) -> None:
        """Verbindet sich mit dem ausgewählten Gerät."""
        self._connection_label.setText(f"Verbinde mit {device.name}...")
        success = await self._connection.connect(device.ble_device)
        if not success:
            self._connection_label.setText("Verbindung fehlgeschlagen")

    def _on_connected(self) -> None:
        name = self._connection.device_name
        addr = self._connection.device_address
        self._connection_label.setText(f"Verbunden: {name} [{addr}]")
        self._status_bar.showMessage("Verbindung hergestellt", 3000)

    def _on_disconnected(self) -> None:
        self._connection_label.setText("Nicht verbunden")
        self._status_bar.showMessage("Verbindung getrennt", 3000)

    def _on_connection_error(self, error: str) -> None:
        self._connection_label.setText("Fehler")
        self._status_bar.showMessage(error, 5000)

    # --- Sende-Operationen ---

    @asyncSlot(str, bool)
    async def _on_send_text(self, text: str, use_font_16: bool) -> None:
        """Sendet Text an das Panel."""
        if not self._connection.is_connected:
            self._status_bar.showMessage("Nicht verbunden!", 3000)
            return

        self._status_bar.showMessage("Sende Text...")
        try:
            # Begin Transfer
            await self._transport.send_packet(cmd_begin_transfer())

            # Mode und Speed setzen
            mode = self._text_tab.selected_mode
            speed = self._text_tab.selected_speed
            await self._transport.send_packet(cmd_mode(mode))
            await self._transport.send_packet(cmd_speed(speed))

            # Text-Pakete kodieren und senden
            packets = encode_text_packets(text, self._font_reader, use_font_16)
            success = await self._transport.send_packets(packets)

            if success:
                self._status_bar.showMessage("Text gesendet!", 3000)
            else:
                self._status_bar.showMessage("Fehler beim Senden", 3000)
        except Exception as e:
            self._status_bar.showMessage(f"Fehler: {e}", 5000)
            logger.error(f"Text-Sende-Fehler: {e}")

    @asyncSlot(bytes)
    async def _on_send_image(self, bitmap: bytes) -> None:
        """Sendet Bitmap-Daten an das Panel."""
        if not self._connection.is_connected:
            self._status_bar.showMessage("Nicht verbunden!", 3000)
            return

        self._status_bar.showMessage("Sende Bild...")
        try:
            await self._transport.send_packet(cmd_begin_transfer())
            success = await self._transport.send_packet(cmd_draw(bitmap))

            if success:
                self._status_bar.showMessage("Bild gesendet!", 3000)
            else:
                self._status_bar.showMessage("Fehler beim Senden", 3000)
        except Exception as e:
            self._status_bar.showMessage(f"Fehler: {e}", 5000)
            logger.error(f"Bild-Sende-Fehler: {e}")

    @asyncSlot(bool)
    async def _on_switch(self, on: bool) -> None:
        if self._connection.is_connected:
            await self._transport.send_packet(cmd_switch(on))

    @asyncSlot(int)
    async def _on_brightness(self, value: int) -> None:
        if self._connection.is_connected:
            await self._transport.send_packet(cmd_brightness(value))

    @asyncSlot(int)
    async def _on_speed(self, value: int) -> None:
        if self._connection.is_connected:
            await self._transport.send_packet(cmd_speed(value))

    @asyncSlot(int)
    async def _on_mode(self, mode: int) -> None:
        if self._connection.is_connected:
            await self._transport.send_packet(cmd_mode(mode))

    @asyncSlot(bytes)
    async def _on_send_raw(self, data: bytes) -> None:
        """Sendet Raw-Hex-Daten ohne zusätzliches Framing."""
        if not self._connection.is_connected:
            self._status_bar.showMessage("Nicht verbunden!", 3000)
            return

        success = await self._transport.send_packet(data)
        if success:
            self._status_bar.showMessage("Raw-Daten gesendet", 3000)

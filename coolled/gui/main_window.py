"""
Hauptfenster der CoolLedDiy Anwendung.

Enthält:
- QTabWidget mit 7 Tabs (Scanner, Text, Bild, Zeichnen, Animation, Controls, Debug)
- Status-Bar mit Verbindungsstatus
- Zentrale Verdrahtung aller Signals zwischen GUI und BLE-Layer
"""

import asyncio
import logging

from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
)
from qasync import asyncSlot

from coolled.ble.connection import BleConnection
from coolled.ble.scanner import DiscoveredDevice
from coolled.ble.transport import BleTransport
from coolled.fonts.font_reader import FontReader
from coolled.gui.animation_tab import AnimationTab
from coolled.gui.control_tab import ControlTab
from coolled.gui.debug_tab import DebugTab
from coolled.gui.drawing_tab import DrawingTab
from coolled.gui.image_tab import ImageTab
from coolled.gui.scanner_tab import ScannerTab
from coolled.gui.text_tab import TextTab
from coolled.models.packet_log import PacketLog
from coolled.protocol.commands import (
    cmd_animation_packets,
    cmd_begin_transfer,
    cmd_brightness,
    cmd_device_info,
    cmd_draw_packets,
    cmd_mirror,
    cmd_mode,
    cmd_speed,
    cmd_switch,
    cmd_sync_time,
)
from coolled.protocol.commands_advanced import (
    build_animation_content,
    build_draw_content,
    build_program_data,
    build_program_transfer,
    build_text_content,
    build_text_content_ux,
    cmd_brightness_m,
    cmd_switch_m,
    cmd_ux_play,
)
from coolled.protocol.constants import BEGIN_TRANSFER_DELAY_S
from coolled.protocol.device_type import (
    DeviceFamily,
    is_ux_family,
    uses_advanced_protocol,
    uses_begin_transfer,
)
from coolled.protocol.text_encoding import encode_text_packets

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Hauptfenster mit Tab-Widget und Verbindungsverwaltung."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CoolLedDiy - LED Matrix Controller")
        self.setMinimumSize(900, 650)

        # BLE-Layer
        self._connection = BleConnection(self)
        self._transport = BleTransport(self._connection, self)
        self._font_reader = FontReader()

        # Gerätefamilie und Panel-Dimensionen (werden beim Connect gesetzt)
        self._device_family: DeviceFamily = DeviceFamily.LIGHT_1248
        self._panel_width: int = 96   # Default Spalten
        self._panel_height: int = 16  # Default Zeilen

        # Paket-Log (zentrale Datenquelle für Debug-Tab)
        self._packet_log = PacketLog(self)

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
        self._drawing_tab = DrawingTab()
        self._animation_tab = AnimationTab()
        self._control_tab = ControlTab()
        self._debug_tab = DebugTab(self._packet_log)

        self._tabs.addTab(self._scanner_tab, "Scanner")
        self._tabs.addTab(self._text_tab, "Text")
        self._tabs.addTab(self._image_tab, "Bild")
        self._tabs.addTab(self._drawing_tab, "Zeichnen")
        self._tabs.addTab(self._animation_tab, "Animation")
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

        # BLE-Daten → PacketLog → Debug-Tab
        self._transport.data_sent.connect(self._packet_log.add_tx)
        self._connection.notify_received.connect(self._packet_log.add_rx)

        # Notify-Daten verarbeiten (z.B. Device-Info Antwort)
        self._connection.notify_received.connect(self._on_notify)

        # Text senden
        self._text_tab.send_text_requested.connect(self._on_send_text)

        # Bild senden
        self._image_tab.send_image_requested.connect(self._on_send_image)

        # Zeichnung senden (nutzt gleichen Handler wie Bild)
        self._drawing_tab.send_drawing_requested.connect(self._on_send_image)

        # Animation senden
        self._animation_tab.send_animation_requested.connect(self._on_send_animation)

        # Controls
        self._control_tab.switch_requested.connect(self._on_switch)
        self._control_tab.brightness_requested.connect(self._on_brightness)
        self._control_tab.speed_requested.connect(self._on_speed)
        self._control_tab.mode_requested.connect(self._on_mode)
        self._control_tab.sync_time_requested.connect(self._on_sync_time)
        self._control_tab.mirror_requested.connect(self._on_mirror)
        self._control_tab.device_info_requested.connect(self._on_device_info)

        # Debug Raw-Send
        self._debug_tab.send_raw_requested.connect(self._on_send_raw)

    # --- Verbindungs-Handling ---

    @asyncSlot(object)
    async def _on_connect_requested(self, device: DiscoveredDevice) -> None:
        """Verbindet sich mit dem ausgewählten Gerät."""
        self._connection_label.setText(f"Verbinde mit {device.name}...")
        # Gerätefamilie aus Scanner-Ergebnis übernehmen
        self._device_family = device.device_family
        # Panel-Dimensionen aus Scan-Record übernehmen (falls verfügbar)
        if device.scan_info:
            self._panel_width = device.scan_info.columns
            self._panel_height = device.scan_info.rows
        logger.info(f"Gerätefamilie: {self._device_family.value}, Panel: {self._panel_width}x{self._panel_height}")
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
        """Sendet Text an das Panel.

        Protokoll-Routing nach Gerätefamilie:
        - Light1248: Direkt Text-Pakete senden (kein begin_transfer)
        - Light536: begin_transfer + 50ms Delay + Text-Pakete
        - UX: Text als RGB444-Bild rendern → Programm-Format mit Response-Waiting
        - M/U: Programm-Format (Start-Paket + LZSS-komprimierte Daten-Pakete)
        """
        if not self._connection.is_connected:
            self._status_bar.showMessage("Nicht verbunden!", 3000)
            return

        self._status_bar.showMessage("Sende Text...")
        try:
            mode = self._text_tab.selected_mode
            speed = self._text_tab.selected_speed

            if is_ux_family(self._device_family):
                # UX: Text als RGB444-Bild rendern und als Draw-Content senden
                # (ESP32-Methode: funktioniert nachweislich)
                success = await self._send_text_as_rgb444(text, mode, speed)
            elif uses_advanced_protocol(self._device_family):
                # M/U: Rohe Font-Bitmap-Daten in Content-Struktur verpacken
                if use_font_16:
                    font_data, _ = self._font_reader.read_text_16(text)
                else:
                    font_data, _ = self._font_reader.read_text_12(text)
                content = build_text_content(
                    font_data, self._panel_width, self._panel_height, mode, speed,
                )
                program_data = build_program_data(content)
                start_pkt, data_pkts = build_program_transfer(program_data)
                await self._transport.send_packet(start_pkt)
                success = await self._transport.send_packets(data_pkts)
            else:
                # Light1248/536: Mode und Speed separat setzen
                await self._transport.send_packet(cmd_mode(mode))
                await self._transport.send_packet(cmd_speed(speed))

                # Light536: begin_transfer + 50ms Delay
                if uses_begin_transfer(self._device_family):
                    await self._transport.send_packet(cmd_begin_transfer())
                    await asyncio.sleep(BEGIN_TRANSFER_DELAY_S)

                # Light1248/536: Text-Pakete direkt senden
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
        """Sendet Bitmap-Daten an das Panel (Bild oder Zeichnung).

        Protokoll-Routing:
        - Light1248: Direkt Draw-Pakete (kein begin_transfer)
        - Light536: begin_transfer + 50ms Delay + Draw-Pakete
        - UX: RGB444-Konvertierung → Programm-Format mit Response-Waiting
        - M/U: Programm-Format (Monochrom-Bitmap)
        """
        if not self._connection.is_connected:
            self._status_bar.showMessage("Nicht verbunden!", 3000)
            return

        self._status_bar.showMessage("Sende Bild...")
        try:
            if is_ux_family(self._device_family):
                # UX: Bitmap als Monochrom-Daten empfangen, zu RGB444 konvertieren
                from coolled.image.converter import bitmap_to_image, image_to_rgb444
                # Bitmap zurück zu PIL-Bild konvertieren, dann als RGB444
                pil_image = bitmap_to_image(bitmap, self._panel_height, self._panel_width)
                rgb444_data = image_to_rgb444(pil_image, self._panel_width, self._panel_height)
                success = await self._send_ux_program(rgb444_data)
            elif uses_advanced_protocol(self._device_family):
                # M/U: Bitmap in Content-Struktur verpacken
                content = build_draw_content(bitmap, self._panel_width, self._panel_height)
                program_data = build_program_data(content)
                start_pkt, data_pkts = build_program_transfer(program_data)
                await self._transport.send_packet(start_pkt)
                success = await self._transport.send_packets(data_pkts)
            else:
                # Light536: begin_transfer + Delay
                if uses_begin_transfer(self._device_family):
                    await self._transport.send_packet(cmd_begin_transfer())
                    await asyncio.sleep(BEGIN_TRANSFER_DELAY_S)

                # Light1248/536: Draw-Pakete direkt
                packets = cmd_draw_packets(bitmap)
                success = await self._transport.send_packets(packets)

            if success:
                self._status_bar.showMessage("Bild gesendet!", 3000)
            else:
                self._status_bar.showMessage("Fehler beim Senden", 3000)
        except Exception as e:
            self._status_bar.showMessage(f"Fehler: {e}", 5000)
            logger.error(f"Bild-Sende-Fehler: {e}")

    async def _send_ux_program(
        self, rgb444_data: bytes, mode: int = 1, speed: int = 1, stay_time: int = 0
    ) -> bool:
        """Sendet RGB444-Pixeldaten als Draw-Content an ein CoolLedUX-Gerät.

        Kompletter UX-Transfer: Start-Paket (mit ACK-Waiting) → Daten-Pakete → Play-Kommando.
        Basiert auf dem funktionierenden ESP32-Referenzcode.

        Args:
            rgb444_data: RGB444-Pixeldaten (2 Bytes pro Pixel, Column-major)
            mode: Display-Modus (1=Statisch)
            speed: Scroll-Geschwindigkeit
            stay_time: Standzeit

        Returns:
            True bei Erfolg
        """
        content = build_draw_content(
            rgb444_data, self._panel_width, self._panel_height, mode, speed, stay_time,
        )
        program_data = build_program_data(content, content_count=1, show_count=0)
        start_pkt, data_pkts = build_program_transfer(
            program_data, content_count=1, show_count=1,
        )

        # Start-Paket senden und auf Bestätigung warten
        if not await self._transport.send_and_wait_response(start_pkt, timeout=3.0):
            logger.warning("UX: Keine Antwort auf Start-Paket, sende trotzdem weiter")

        # Komprimierte Daten-Pakete senden
        success = await self._transport.send_packets(data_pkts)
        if not success:
            return False

        # Play-Kommando senden (finalisiert den Transfer)
        await asyncio.sleep(0.1)
        await self._transport.send_packet(cmd_ux_play())
        return True

    async def _send_text_as_rgb444(self, text: str, mode: int, speed: int) -> bool:
        """Rendert Text als RGB444-Bild und sendet es an ein CoolLedUX-Gerät.

        ESP32-Methode: Text lokal als weißes Bild rendern, zu RGB444 konvertieren,
        als Draw-Content senden. Funktioniert nachweislich.

        Args:
            text: Zu sendender Text
            mode: Display-Modus
            speed: Scroll-Geschwindigkeit

        Returns:
            True bei Erfolg
        """
        from PIL import Image, ImageDraw, ImageFont
        from coolled.image.converter import image_to_rgb444

        w, h = self._panel_width, self._panel_height

        # Text mit PIL rendern (weiß auf schwarz)
        img = Image.new("RGB", (w, h), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Eingebauten Font verwenden, passend zur Panel-Höhe
        try:
            font = ImageFont.truetype("arial.ttf", max(8, h - 4))
        except OSError:
            font = ImageFont.load_default()

        # Text zentrieren
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = max(0, (w - text_w) // 2)
        y = max(0, (h - text_h) // 2) - bbox[1]
        draw.text((x, y), text, fill=(255, 255, 255), font=font)

        # Zu RGB444 konvertieren und senden
        rgb444_data = image_to_rgb444(img, w, h)
        return await self._send_ux_program(rgb444_data, mode, speed)

    @asyncSlot(list, int)
    async def _on_send_animation(self, frames: list, speed: int) -> None:
        """Sendet eine Multi-Frame-Animation an das Panel.

        Protokoll-Routing:
        - Light1248: begin_transfer + Animation-Pakete (Animation braucht immer begin_transfer)
        - Light536: begin_transfer + 50ms Delay + Animation-Pakete
        - M/U/UX: Programm-Format
        """
        if not self._connection.is_connected:
            self._status_bar.showMessage("Nicht verbunden!", 3000)
            return

        self._status_bar.showMessage("Sende Animation...")
        try:
            if uses_advanced_protocol(self._device_family):
                # M/U/UX: Rohe Frame-Daten in Content-Struktur verpacken
                # (frames ist list[bytes] mit Bitmap-Daten pro Frame)
                raw_anim = b"".join(frames)
                content = build_animation_content(
                    raw_anim, self._panel_width, self._panel_height, speed,
                )
                program_data = build_program_data(content)
                start_pkt, data_pkts = build_program_transfer(program_data)
                await self._transport.send_packet(start_pkt)
                success = await self._transport.send_packets(data_pkts)
            else:
                # Light1248/536: begin_transfer + Animation-Pakete
                await self._transport.send_packet(cmd_begin_transfer())
                if uses_begin_transfer(self._device_family):
                    await asyncio.sleep(BEGIN_TRANSFER_DELAY_S)
                packets = cmd_animation_packets(frames, speed)
                success = await self._transport.send_packets(packets)

            if success:
                self._status_bar.showMessage("Animation gesendet!", 3000)
            else:
                self._status_bar.showMessage("Fehler beim Senden", 3000)
        except Exception as e:
            self._status_bar.showMessage(f"Fehler: {e}", 5000)
            logger.error(f"Animation-Sende-Fehler: {e}")

    @asyncSlot(bool)
    async def _on_switch(self, on: bool) -> None:
        if self._connection.is_connected:
            if uses_advanced_protocol(self._device_family):
                await self._transport.send_packet(cmd_switch_m(on))
            else:
                await self._transport.send_packet(cmd_switch(on))

    @asyncSlot(int)
    async def _on_brightness(self, value: int) -> None:
        if self._connection.is_connected:
            if uses_advanced_protocol(self._device_family):
                await self._transport.send_packet(cmd_brightness_m(value))
            else:
                await self._transport.send_packet(cmd_brightness(value))

    @asyncSlot(int)
    async def _on_speed(self, value: int) -> None:
        if self._connection.is_connected:
            if uses_advanced_protocol(self._device_family):
                self._status_bar.showMessage(
                    "Speed wird beim Senden im Content-Header gesetzt", 3000)
                return
            await self._transport.send_packet(cmd_speed(value))

    @asyncSlot(int)
    async def _on_mode(self, mode: int) -> None:
        if self._connection.is_connected:
            if uses_advanced_protocol(self._device_family):
                self._status_bar.showMessage(
                    "Modus wird beim Senden im Content-Header gesetzt", 3000)
                return
            await self._transport.send_packet(cmd_mode(mode))

    @asyncSlot()
    async def _on_sync_time(self) -> None:
        """Synchronisiert die PC-Uhrzeit mit dem Gerät."""
        if self._connection.is_connected:
            await self._transport.send_packet(cmd_sync_time())
            self._status_bar.showMessage("Zeit synchronisiert", 3000)

    @asyncSlot(bool)
    async def _on_mirror(self, enabled: bool) -> None:
        """Aktiviert/deaktiviert die Display-Spiegelung."""
        if self._connection.is_connected:
            await self._transport.send_packet(cmd_mirror(enabled))
            self._status_bar.showMessage(
                f"Spiegelung {'aktiviert' if enabled else 'deaktiviert'}", 3000
            )

    @asyncSlot()
    async def _on_device_info(self) -> None:
        """Fragt Geräteinformationen ab."""
        if self._connection.is_connected:
            await self._transport.send_packet(cmd_device_info())
            self._status_bar.showMessage("Geräteinformation angefragt", 3000)

    def _on_notify(self, data: bytes) -> None:
        """Verarbeitet empfangene BLE-Notify-Daten."""
        from coolled.protocol.framing import unframe_packet
        payload = unframe_packet(data)
        if payload and len(payload) > 1 and payload[0] == 0x1F:  # CMD_DEVICE_INFO
            # Rohe Hex-Darstellung der Antwort anzeigen
            info_hex = payload[1:].hex(" ")
            self._control_tab.set_device_info(f"Device-Info Response:\n{info_hex}")

    @asyncSlot(bytes)
    async def _on_send_raw(self, data: bytes) -> None:
        """Sendet Raw-Hex-Daten ohne zusätzliches Framing."""
        if not self._connection.is_connected:
            self._status_bar.showMessage("Nicht verbunden!", 3000)
            return

        success = await self._transport.send_packet(data)
        if success:
            self._status_bar.showMessage("Raw-Daten gesendet", 3000)

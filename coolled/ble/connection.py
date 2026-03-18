"""
BLE Connection Manager für CoolLed Geräte.

Verwaltet die Verbindung zu einem CoolLed BLE-Gerät:
connect, disconnect, MTU-Negotiation, Notify-Setup, Write.

Basiert auf DeviceManager.java (BLE_MTU_MAX_SIZE, UUID_SERVICE, UUID_CHARACTER).
"""

import asyncio
import logging

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from PySide6.QtCore import QObject, Signal

from coolled.protocol.constants import (
    BLE_MTU_MAX_SIZE,
    BLE_WRITE_CHAR_MAX_SIZE,
    BLE_WRITE_CHAR_MIN_SIZE,
    UUID_CHARACTERISTIC,
    UUID_SERVICE,
)

logger = logging.getLogger(__name__)


class BleConnection(QObject):
    """Verwaltet eine BLE-Verbindung zu einem CoolLed Gerät.

    Emittiert Qt Signals für Verbindungsstatus und empfangene Daten,
    damit der Debug-Tab und andere GUI-Komponenten reagieren können.
    """

    # Signals für GUI-Entkopplung
    connected = Signal()
    disconnected = Signal()
    notify_received = Signal(bytes)  # Empfangene Daten vom Gerät
    connection_error = Signal(str)   # Fehlermeldung

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._client: BleakClient | None = None
        self._device: BLEDevice | None = None
        self._mtu: int = BLE_WRITE_CHAR_MIN_SIZE  # Startwert, wird nach MTU-Negotiation angepasst
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Gibt True zurück wenn eine aktive Verbindung besteht."""
        return self._is_connected and self._client is not None and self._client.is_connected

    @property
    def write_chunk_size(self) -> int:
        """Maximale Chunk-Größe für BLE-Writes basierend auf aktuellem MTU."""
        return self._mtu

    @property
    def device_name(self) -> str:
        """Name des verbundenen Geräts oder leer."""
        if self._device:
            return self._device.name or self._device.address
        return ""

    @property
    def device_address(self) -> str:
        """MAC-Adresse des verbundenen Geräts oder leer."""
        if self._device:
            return self._device.address
        return ""

    def _on_disconnect(self, client: BleakClient) -> None:
        """Disconnect-Callback von bleak."""
        logger.info(f"Verbindung getrennt: {self.device_name}")
        self._is_connected = False
        self.disconnected.emit()

    def _on_notify(self, sender: int, data: bytearray) -> None:
        """Notify-Callback: empfängt Daten vom Gerät."""
        logger.debug(f"Notify empfangen ({len(data)} Bytes): {data.hex()}")
        self.notify_received.emit(bytes(data))

    async def connect(self, device: BLEDevice) -> bool:
        """Verbindet sich mit einem CoolLed BLE-Gerät.

        Führt aus:
        1. BLE-Verbindung aufbauen
        2. MTU-Negotiation (Request 247)
        3. Notify auf Characteristic einrichten

        Args:
            device: BLEDevice vom Scanner

        Returns:
            True bei erfolgreicher Verbindung
        """
        if self.is_connected:
            await self.disconnect()

        self._device = device
        logger.info(f"Verbinde mit {device.name} [{device.address}]...")

        try:
            self._client = BleakClient(
                device,
                disconnected_callback=self._on_disconnect,
            )
            await self._client.connect()

            # MTU-Negotiation (Ref: DeviceManager.java BLE_MTU_MAX_SIZE = 247)
            # bleak's mtu_size gibt den negotiated MTU inkl. 3 Byte ATT-Overhead.
            # Nutzbare Payload = MTU - 3. Bei MTU 247 → 244, gekappt auf 180.
            try:
                mtu = self._client.mtu_size
                usable = (mtu - 3) if mtu else 0
                if usable > BLE_WRITE_CHAR_MIN_SIZE:
                    self._mtu = min(usable, BLE_WRITE_CHAR_MAX_SIZE)
                else:
                    self._mtu = BLE_WRITE_CHAR_MIN_SIZE
                logger.info(f"MTU: {mtu}, Usable: {usable}, Write-Chunk-Size: {self._mtu}")
            except Exception:
                self._mtu = BLE_WRITE_CHAR_MIN_SIZE
                logger.warning("MTU-Abfrage fehlgeschlagen, verwende Fallback 20 Bytes")

            # Notify einrichten auf der Characteristic
            try:
                await self._client.start_notify(UUID_CHARACTERISTIC, self._on_notify)
                logger.info("Notify eingerichtet")
            except Exception as e:
                logger.warning(f"Notify-Setup fehlgeschlagen: {e}")

            self._is_connected = True
            self.connected.emit()
            logger.info(f"Verbunden mit {device.name}")
            return True

        except Exception as e:
            error_msg = f"Verbindungsfehler: {e}"
            logger.error(error_msg)
            self.connection_error.emit(error_msg)
            self._is_connected = False
            return False

    async def disconnect(self) -> None:
        """Trennt die BLE-Verbindung."""
        if self._client and self._client.is_connected:
            try:
                await self._client.stop_notify(UUID_CHARACTERISTIC)
            except Exception:
                pass
            try:
                await self._client.disconnect()
            except Exception:
                pass
        self._is_connected = False
        self._client = None
        logger.info("Verbindung getrennt")

    async def write(self, data: bytes) -> bool:
        """Schreibt Daten an die CoolLed Characteristic.

        Args:
            data: Zu sendende Bytes (sollte bereits geframed sein)

        Returns:
            True bei Erfolg
        """
        if not self.is_connected or not self._client:
            logger.warning("Kann nicht senden: Nicht verbunden")
            return False

        try:
            await self._client.write_gatt_char(UUID_CHARACTERISTIC, data, response=False)
            return True
        except Exception as e:
            logger.error(f"Write-Fehler: {e}")
            return False

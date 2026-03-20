"""
High-Level BLE Transport für CoolLed Geräte.

Kümmert sich um:
- Aufteilen von Paketen in Chunks nach MTU-Größe
- 15ms Delay zwischen Chunks (INTERNAL_BETWEEN_TWO_PACKAGE)
- Send-Queue für sequentielle Übertragung
- Debug-Signals für TX-Monitoring

Basiert auf DeviceManager.java (BLE_WRITE_CHAR_MAX_SIZE, INTERNAL_BETWEEN_TWO_PACKAGE).
"""

import asyncio
import logging

from PySide6.QtCore import QObject, Signal

from coolled.ble.connection import BleConnection
from coolled.protocol.constants import PACKET_DELAY_MS

logger = logging.getLogger(__name__)


class BleTransport(QObject):
    """High-Level Transport-Layer über einer BleConnection.

    Teilt große Pakete in MTU-gerechte Chunks auf und sendet sie
    mit dem korrekten Delay von 15ms zwischen den Chunks.
    """

    # Signals für Debug-Monitoring
    data_sent = Signal(bytes)       # Wird nach jedem gesendeten Chunk emittiert
    send_complete = Signal()        # Gesamte Übertragung abgeschlossen
    send_error = Signal(str)        # Fehler beim Senden

    def __init__(self, connection: BleConnection, parent: QObject | None = None):
        super().__init__(parent)
        self._connection = connection
        self._sending = False

    @property
    def is_connected(self) -> bool:
        """Gibt True zurück wenn die darunterliegende Verbindung aktiv ist."""
        return self._connection.is_connected

    async def send_packet(self, data: bytes) -> bool:
        """Sendet ein einzelnes Paket, bei Bedarf in Chunks aufgeteilt.

        Teilt das Paket in Chunks der maximalen Write-Größe auf und
        sendet diese mit 15ms Delay dazwischen.

        Args:
            data: Frame-Paket (Ergebnis von frame_packet() oder cmd_*())

        Returns:
            True wenn alle Chunks erfolgreich gesendet wurden
        """
        if not self._connection.is_connected:
            self.send_error.emit("Nicht verbunden")
            return False

        chunk_size = self._connection.write_chunk_size
        chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

        logger.debug(f"Sende {len(data)} Bytes in {len(chunks)} Chunk(s) (MTU={chunk_size})")

        for i, chunk in enumerate(chunks):
            success = await self._connection.write(chunk)
            if not success:
                error_msg = f"Chunk {i+1}/{len(chunks)} fehlgeschlagen"
                logger.error(error_msg)
                self.send_error.emit(error_msg)
                return False

            self.data_sent.emit(chunk)

            # 15ms Delay zwischen Chunks (Ref: INTERNAL_BETWEEN_TWO_PACKAGE = 15)
            if i < len(chunks) - 1:
                await asyncio.sleep(PACKET_DELAY_MS / 1000.0)

        return True

    async def send_packets(self, packets: list[bytes]) -> bool:
        """Sendet mehrere Pakete sequentiell.

        Nützlich für Text-Übertragung die aus mehreren Frame-Paketen besteht.

        Args:
            packets: Liste von Frame-Paketen

        Returns:
            True wenn alle Pakete erfolgreich gesendet wurden
        """
        self._sending = True
        logger.info(f"Starte Übertragung von {len(packets)} Paket(en)")

        for i, packet in enumerate(packets):
            if not self._sending:
                logger.info("Übertragung abgebrochen")
                return False

            logger.debug(f"Sende Paket {i+1}/{len(packets)} ({len(packet)} Bytes)")
            success = await self.send_packet(packet)
            if not success:
                self._sending = False
                return False

            # Kurzer Delay zwischen Paketen
            if i < len(packets) - 1:
                await asyncio.sleep(PACKET_DELAY_MS / 1000.0)

        self._sending = False
        self.send_complete.emit()
        logger.info("Übertragung abgeschlossen")
        return True

    async def send_and_wait_response(self, data: bytes, timeout: float = 3.0) -> bool:
        """Sendet ein Paket und wartet auf BLE-Notification als Bestätigung.

        Wird für UX-Geräte nach dem Start-Paket verwendet. Das Gerät sendet
        eine Antwort bevor es bereit für Daten-Pakete ist.
        Basiert auf ESP32-Referenzcode: sendStartPacket() + waitRX(3000).

        Args:
            data: Frame-Paket zum Senden
            timeout: Wartezeit auf Antwort in Sekunden

        Returns:
            True wenn Paket gesendet und Antwort empfangen wurde
        """
        success = await self.send_packet(data)
        if not success:
            return False

        response = await self._connection.wait_for_notification(timeout)
        if response is None:
            logger.warning("Keine Antwort auf Paket erhalten")
            return False

        logger.debug(f"Antwort erhalten: {response.hex()}")
        return True

    def cancel_send(self) -> None:
        """Bricht eine laufende Übertragung ab."""
        self._sending = False
        logger.info("Übertragung wird abgebrochen...")

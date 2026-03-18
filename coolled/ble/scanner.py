"""
Async BLE Scanner für CoolLed Geräte.

Verwendet bleak.BleakScanner um BLE-Geräte zu finden und nach
bekannten CoolLed-Gerätenamen zu filtern.
"""

import logging
from dataclasses import dataclass

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from coolled.protocol.constants import DEVICE_NAMES
from coolled.protocol.scan_record import ScanRecordInfo, parse_scan_record

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredDevice:
    """Ein gefundenes CoolLed BLE-Gerät mit geparsten Informationen."""

    ble_device: BLEDevice          # bleak BLEDevice für Verbindung
    name: str                      # Gerätename
    address: str                   # MAC-Adresse
    rssi: int                      # Signalstärke
    scan_info: ScanRecordInfo | None  # Geparste Scan-Record-Daten (falls verfügbar)
    raw_manufacturer_data: dict    # Rohe Manufacturer-Data aus Advertisement


class BleScanner:
    """BLE Scanner der nach CoolLed Geräten sucht.

    Filtert gefundene Geräte nach bekannten CoolLed-Gerätenamen und
    versucht Scan-Record-Informationen zu parsen.
    """

    def __init__(self):
        self._discovered: dict[str, DiscoveredDevice] = {}

    def _detection_callback(self, device: BLEDevice, adv_data: AdvertisementData) -> None:
        """Callback für jeden gefundenen BLE-Gerät während des Scans."""
        name = adv_data.local_name or device.name or ""

        # Nur bekannte CoolLed-Gerätenamen durchlassen
        if not any(name.startswith(prefix) for prefix in DEVICE_NAMES):
            return

        # Scan-Record aus Manufacturer-Data rekonstruieren
        # bleak gibt manufacturer_data als Dict {company_id: bytes}
        scan_info = None
        raw_mfr = adv_data.manufacturer_data
        for company_id, mfr_data in raw_mfr.items():
            # Versuche Scan-Record-Felder aus den Manufacturer-Daten zu parsen
            # Das Layout kann von der Android-Variante abweichen
            scan_info = _try_parse_manufacturer_data(company_id, mfr_data)
            if scan_info:
                break

        discovered = DiscoveredDevice(
            ble_device=device,
            name=name,
            address=device.address,
            rssi=adv_data.rssi,
            scan_info=scan_info,
            raw_manufacturer_data=raw_mfr,
        )

        self._discovered[device.address] = discovered
        logger.debug(f"Gefunden: {name} [{device.address}] RSSI={adv_data.rssi}")

    async def scan(self, timeout: float = 5.0) -> list[DiscoveredDevice]:
        """Scannt nach CoolLed BLE-Geräten.

        Args:
            timeout: Scan-Dauer in Sekunden

        Returns:
            Liste der gefundenen CoolLed-Geräte
        """
        self._discovered.clear()
        logger.info(f"Starte BLE-Scan für {timeout}s...")

        scanner = BleakScanner(detection_callback=self._detection_callback)
        await scanner.start()

        import asyncio
        await asyncio.sleep(timeout)
        await scanner.stop()

        devices = list(self._discovered.values())
        logger.info(f"Scan beendet: {len(devices)} CoolLed-Gerät(e) gefunden")
        return devices


def _try_parse_manufacturer_data(company_id: int, data: bytes) -> ScanRecordInfo | None:
    """Versucht Scan-Record-Infos aus Manufacturer-Data zu extrahieren.

    Auf Windows/bleak ist das Format anders als auf Android.
    Die Company-ID 0x1234 und die Daten-Bytes werden direkt interpretiert.
    """
    # Heuristik: Wenn genug Daten vorhanden, versuchen wir die
    # relevanten Felder ab bestimmten Offsets zu parsen
    if len(data) < 16:
        return None

    try:
        # Versuch: die relevanten Felder in den Manufacturer-Daten zu finden
        # Offset-Anpassung: in bleak sind die Daten ohne den Scan-Record-Header
        # Wir versuchen die Felder relativ zum Datenstart
        rows = data[11] if len(data) > 11 else 0
        cols = ((data[12] << 8) | data[13]) if len(data) > 13 else 0
        color_type = data[14] if len(data) > 14 else 0
        fw_version = data[15] if len(data) > 15 else 0

        # Plausibilitätscheck
        if rows == 0 or cols == 0 or rows > 64 or cols > 512:
            return None

        return ScanRecordInfo(
            device_id=company_id,
            rows=rows,
            columns=cols,
            color_type=color_type,
            fw_version=fw_version,
        )
    except (IndexError, ValueError):
        return None

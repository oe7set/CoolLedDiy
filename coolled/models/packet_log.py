"""
Zentrales Paket-Log für BLE-Kommunikation.

Speichert alle TX/RX-Pakete mit Metadaten (Timestamp, Richtung, Kommando, etc.)
und bietet Filterung, Export und Statistik-Funktionen.
Wird vom Debug-Tab als Datenquelle verwendet.
"""

import csv
from dataclasses import dataclass, field
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from coolled.protocol.constants import CMD_NAMES, MODE_NAMES
from coolled.protocol.framing import unframe_packet


@dataclass
class PacketEntry:
    """Einzelner Eintrag im Paket-Log."""

    index: int                     # Laufende Nummer
    timestamp: datetime            # Zeitpunkt
    direction: str                 # "TX" oder "RX"
    raw_data: bytes                # Rohdaten wie empfangen/gesendet
    payload: bytes | None = None   # Entframter Payload (None bei ungültigem Frame)
    command: int | None = None     # Kommando-Byte (erstes Byte des Payload)
    command_name: str = ""         # Menschenlesbarer Kommando-Name
    summary: str = ""              # Kurzbeschreibung (auto-generiert)


def _generate_summary(payload: bytes | None) -> str:
    """Erzeugt eine menschenlesbare Zusammenfassung des Pakets."""
    if payload is None or len(payload) == 0:
        return "Ungültiges Paket"

    cmd = payload[0]
    data = payload[1:]

    # Kommando-spezifische Zusammenfassung
    if cmd == 0x08 and len(data) >= 1:  # BRIGHTNESS
        return f"Helligkeit: {data[0]}"
    elif cmd == 0x07 and len(data) >= 1:  # SPEED
        return f"Geschwindigkeit: {data[0]}"
    elif cmd == 0x09 and len(data) >= 1:  # SWITCH / SYNC_TIME
        if len(data) == 1:
            return f"Display: {'EIN' if data[0] else 'AUS'}"
        elif len(data) >= 7:
            # Time sync: year, month, day, weekday, hour, min, sec
            return (f"Zeit-Sync: {2000 + data[0]:04d}-{data[1]:02d}-{data[2]:02d} "
                    f"{data[4]:02d}:{data[5]:02d}:{data[6]:02d}")
        return f"Switch/Sync: {data.hex(' ')}"
    elif cmd == 0x06 and len(data) >= 1:  # MODE
        mode_name = MODE_NAMES.get(data[0], f"0x{data[0]:02X}")
        return f"Modus: {mode_name}"
    elif cmd == 0x03:  # DRAW
        return f"Bitmap: {len(data)} Bytes"
    elif cmd == 0x02:  # TEXT
        return f"Text-Daten: {len(data)} Bytes"
    elif cmd == 0x04:  # ANIMATION
        return f"Animation: {len(data)} Bytes"
    elif cmd == 0x0A:  # BEGIN_TRANSFER
        return "Transfer-Start"
    elif cmd == 0x0C and len(data) >= 1:  # MIRROR
        return f"Spiegelung: {'EIN' if data[0] else 'AUS'}"
    elif cmd == 0x1F:  # DEVICE_INFO
        if len(data) > 0:
            return f"Geräteinfo: {data.hex(' ')}"
        return "Geräteinfo angefragt"
    elif cmd == 0x01:  # MUSIC
        return f"Musik: {len(data)} Bytes"
    elif cmd == 0x05:  # ICON
        return f"Icon: {len(data)} Bytes"

    return f"Cmd 0x{cmd:02X}: {len(data)} Bytes"


class PacketLog(QObject):
    """Zentrales Paket-Log mit Signal-basierter UI-Benachrichtigung.

    Speichert alle BLE-Pakete, bietet Filterung, Export und Echtzeit-Statistiken.
    """

    # Signals
    packet_added = Signal(int)    # Index des neuen Pakets
    log_cleared = Signal()        # Log wurde gelöscht

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[PacketEntry] = []
        self._start_time = datetime.now()

    def _add_entry(self, direction: str, data: bytes) -> PacketEntry:
        """Internes Hinzufügen eines Eintrags mit Auto-Analyse."""
        payload = unframe_packet(data)
        command = payload[0] if payload and len(payload) > 0 else None
        command_name = CMD_NAMES.get(command, f"0x{command:02X}") if command is not None else ""
        summary = _generate_summary(payload)

        entry = PacketEntry(
            index=len(self._entries),
            timestamp=datetime.now(),
            direction=direction,
            raw_data=data,
            payload=payload,
            command=command,
            command_name=command_name,
            summary=summary,
        )
        self._entries.append(entry)
        self.packet_added.emit(entry.index)
        return entry

    def add_tx(self, data: bytes) -> PacketEntry:
        """Loggt gesendete Daten (TX)."""
        return self._add_entry("TX", data)

    def add_rx(self, data: bytes) -> PacketEntry:
        """Loggt empfangene Daten (RX)."""
        return self._add_entry("RX", data)

    def get(self, index: int) -> PacketEntry | None:
        """Gibt einen Eintrag nach Index zurück."""
        if 0 <= index < len(self._entries):
            return self._entries[index]
        return None

    def count(self) -> int:
        """Gesamtanzahl der Einträge."""
        return len(self._entries)

    def clear(self) -> None:
        """Löscht das gesamte Log."""
        self._entries.clear()
        self._start_time = datetime.now()
        self.log_cleared.emit()

    def all_entries(self) -> list[PacketEntry]:
        """Gibt alle Einträge zurück."""
        return list(self._entries)

    def filter_entries(
        self,
        direction: str | None = None,
        command: int | None = None,
        hex_search: str | None = None,
        text_search: str | None = None,
    ) -> list[PacketEntry]:
        """Filtert Einträge nach Kriterien.

        Args:
            direction: "TX" oder "RX" (None = alle)
            command: Kommando-Byte filtern (None = alle)
            hex_search: Hex-Byte-Sequenz suchen, z.B. "FF 00" (None = kein Filter)
            text_search: Suche im Summary-Text (None = kein Filter)
        """
        results = self._entries

        if direction:
            results = [e for e in results if e.direction == direction]

        if command is not None:
            results = [e for e in results if e.command == command]

        if hex_search:
            # Hex-Suchstring in Bytes umwandeln
            try:
                search_bytes = bytes.fromhex(hex_search.replace(" ", ""))
                results = [e for e in results if search_bytes in e.raw_data]
            except ValueError:
                pass  # Ungültiger Hex-String, Filter ignorieren

        if text_search:
            text_lower = text_search.lower()
            results = [e for e in results
                       if text_lower in e.summary.lower()
                       or text_lower in e.command_name.lower()]

        return results

    def export_csv(self, path: str) -> None:
        """Exportiert das Log als CSV-Datei."""
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["#", "Timestamp", "Direction", "Length", "Command", "Summary", "Hex"])
            for entry in self._entries:
                writer.writerow([
                    entry.index,
                    entry.timestamp.strftime("%H:%M:%S.%f")[:-3],
                    entry.direction,
                    len(entry.raw_data),
                    entry.command_name,
                    entry.summary,
                    entry.raw_data.hex(" "),
                ])

    def export_hex_dump(self, path: str) -> None:
        """Exportiert das Log als Hex-Dump-Textdatei."""
        with open(path, "w", encoding="utf-8") as f:
            for entry in self._entries:
                ts = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]
                hex_str = entry.raw_data.hex(" ")
                ascii_str = "".join(
                    chr(b) if 32 <= b < 127 else "." for b in entry.raw_data
                )
                f.write(f"[{ts}] {entry.direction} | {hex_str} | {ascii_str}\n")

    @property
    def stats(self) -> dict:
        """Berechnet Echtzeit-Statistiken über die Kommunikation."""
        tx_entries = [e for e in self._entries if e.direction == "TX"]
        rx_entries = [e for e in self._entries if e.direction == "RX"]

        tx_bytes = sum(len(e.raw_data) for e in tx_entries)
        rx_bytes = sum(len(e.raw_data) for e in rx_entries)

        # Kommando-Verteilung
        cmd_dist: dict[str, int] = {}
        for e in self._entries:
            name = e.command_name or "UNKNOWN"
            cmd_dist[name] = cmd_dist.get(name, 0) + 1

        # Datenrate (letzte 10 Sekunden)
        now = datetime.now()
        recent_bytes = sum(
            len(e.raw_data) for e in self._entries
            if (now - e.timestamp).total_seconds() <= 10.0
        )
        data_rate = recent_bytes / 10.0

        # Sitzungsdauer
        duration = (now - self._start_time).total_seconds()

        return {
            "tx_count": len(tx_entries),
            "rx_count": len(rx_entries),
            "tx_bytes": tx_bytes,
            "rx_bytes": rx_bytes,
            "data_rate": data_rate,
            "duration": duration,
            "command_distribution": cmd_dist,
        }

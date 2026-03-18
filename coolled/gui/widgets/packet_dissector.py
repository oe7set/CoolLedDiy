"""
Paket-Dissector Widget für den Debug-Tab.

Zeigt eine detaillierte Feld-für-Feld-Analyse eines einzelnen BLE-Pakets:
Frame-Marker, Escaped/Unescaped Payload, Kommando-ID, kommandospezifische
Felder, Hex+ASCII Dump.
"""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget

from coolled.models.packet_log import PacketEntry
from coolled.protocol.constants import CMD_NAMES, MODE_NAMES
from coolled.protocol.framing import FRAME_END, FRAME_START, unescape_data


class PacketDissectorWidget(QWidget):
    """Detaillierte Feld-für-Feld-Analyse eines einzelnen Pakets."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas", 9))
        self._text.setStyleSheet(
            "QTextEdit { background-color: #1a1a2e; color: #e0e0e0; }"
        )
        layout.addWidget(self._text)

    def clear(self) -> None:
        """Löscht die Anzeige."""
        self._text.clear()

    def set_packet(self, entry: PacketEntry) -> None:
        """Analysiert und zeigt ein Paket detailliert an."""
        lines = []
        data = entry.raw_data

        # Header
        lines.append(f"═══ Paket #{entry.index} ({entry.direction}) ═══")
        lines.append(f"Zeitpunkt: {entry.timestamp.strftime('%H:%M:%S.%f')[:-3]}")
        lines.append(f"Richtung:  {entry.direction}")
        lines.append("")

        # Raw Hex Dump + ASCII
        lines.append(f"── Raw Daten ({len(data)} Bytes) ──")
        lines.append(self._hex_dump(data))
        lines.append("")

        # Frame-Analyse
        lines.append("── Frame-Analyse ──")
        if len(data) >= 2 and data[0] == FRAME_START and data[-1] == FRAME_END:
            lines.append(f"Start-Marker: 0x{FRAME_START:02X} ✓")
            lines.append(f"End-Marker:   0x{FRAME_END:02X} ✓")

            # Escaped Inhalt
            inner_escaped = data[1:-1]
            lines.append(f"Escaped Payload ({len(inner_escaped)} Bytes): {inner_escaped.hex(' ')}")

            # Unescaped
            inner_unescaped = unescape_data(inner_escaped)
            lines.append(f"Unescaped ({len(inner_unescaped)} Bytes): {inner_unescaped.hex(' ')}")

            # Length-Prefix
            if len(inner_unescaped) >= 2:
                length_val = (inner_unescaped[0] << 8) | inner_unescaped[1]
                lines.append(f"Length-Prefix: {length_val} (0x{inner_unescaped[0]:02X} 0x{inner_unescaped[1]:02X})")

                payload = inner_unescaped[2:]
                actual_len = len(payload)
                match = "✓" if actual_len == length_val else f"✗ (tatsächlich {actual_len})"
                lines.append(f"Payload-Länge: {actual_len} {match}")
            else:
                payload = None
                lines.append("Payload: zu kurz für Length-Prefix")
        else:
            lines.append("Kein gültiger Frame (erwartet: 0x01...0x03)")
            payload = None

        lines.append("")

        # Kommando-Analyse
        if entry.payload and len(entry.payload) > 0:
            cmd = entry.payload[0]
            cmd_name = CMD_NAMES.get(cmd, f"UNBEKANNT")
            lines.append("── Kommando ──")
            lines.append(f"Kommando-Byte: 0x{cmd:02X} ({cmd_name})")

            cmd_data = entry.payload[1:]
            if cmd_data:
                lines.append(f"Kommando-Daten ({len(cmd_data)} Bytes): {cmd_data.hex(' ')}")
                lines.append("")

                # Kommando-spezifische Felder
                lines.append("── Felder ──")
                lines.extend(self._dissect_command(cmd, cmd_data))
            else:
                lines.append("Keine Kommando-Daten")

        self._text.setPlainText("\n".join(lines))

    def _hex_dump(self, data: bytes) -> str:
        """Erzeugt einen formatierten Hex-Dump mit ASCII-Sidebar."""
        lines = []
        for offset in range(0, len(data), 16):
            chunk = data[offset:offset + 16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            # 16 Bytes = 47 Zeichen Hex, padding für kurze Zeilen
            hex_part = hex_part.ljust(47)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"  {offset:04X}  {hex_part}  {ascii_part}")
        return "\n".join(lines)

    def _dissect_command(self, cmd: int, data: bytes) -> list[str]:
        """Erzeugt kommandospezifische Feld-Beschreibungen."""
        lines = []

        if cmd == 0x08 and len(data) >= 1:  # BRIGHTNESS
            lines.append(f"Helligkeit: {data[0]} (0x{data[0]:02X})")

        elif cmd == 0x07 and len(data) >= 1:  # SPEED
            lines.append(f"Geschwindigkeit: {data[0]} (0x{data[0]:02X})")

        elif cmd == 0x06 and len(data) >= 1:  # MODE
            mode_name = MODE_NAMES.get(data[0], "Unbekannt")
            lines.append(f"Display-Modus: {data[0]} = {mode_name}")

        elif cmd == 0x09:  # SWITCH / SYNC_TIME
            if len(data) == 1:
                lines.append(f"Display-Status: {'EIN' if data[0] else 'AUS'} (0x{data[0]:02X})")
            elif len(data) >= 7:
                lines.append(f"Jahr:     20{data[0]:02d}")
                lines.append(f"Monat:    {data[1]:02d}")
                lines.append(f"Tag:      {data[2]:02d}")
                weekdays = {1: "Mo", 2: "Di", 3: "Mi", 4: "Do", 5: "Fr", 6: "Sa", 7: "So"}
                lines.append(f"Wochentag: {data[3]} = {weekdays.get(data[3], '?')}")
                lines.append(f"Stunde:   {data[4]:02d}")
                lines.append(f"Minute:   {data[5]:02d}")
                lines.append(f"Sekunde:  {data[6]:02d}")

        elif cmd == 0x0C and len(data) >= 1:  # MIRROR
            lines.append(f"Spiegelung: {'EIN' if data[0] else 'AUS'} (0x{data[0]:02X})")

        elif cmd == 0x1F:  # DEVICE_INFO
            if len(data) > 0:
                lines.append(f"Info-Daten: {data.hex(' ')}")
                # Versuch einer Interpretation
                if len(data) >= 4:
                    lines.append(f"  Byte 0: 0x{data[0]:02X}")
                    lines.append(f"  Byte 1: 0x{data[1]:02X}")
                    lines.append(f"  Byte 2: 0x{data[2]:02X}")
                    lines.append(f"  Byte 3: 0x{data[3]:02X}")
            else:
                lines.append("Anfrage (keine Daten)")

        elif cmd == 0x03:  # DRAW
            lines.append(f"Bitmap-Daten: {len(data)} Bytes")
            if len(data) > 0:
                lines.append(f"  Erste 16 Bytes: {data[:16].hex(' ')}")

        elif cmd == 0x02:  # TEXT
            lines.append(f"Text-Chunk-Daten: {len(data)} Bytes")
            if len(data) >= 6:
                # Chunk-Metadata: [seq, total_len_hi, total_len_lo, chunk_idx_hi, chunk_idx_lo, chunk_size]
                lines.append(f"  Sequenz:    0x{data[0]:02X}")
                total = (data[1] << 8) | data[2]
                lines.append(f"  Total-Len:  {total}")
                chunk_idx = (data[3] << 8) | data[4]
                lines.append(f"  Chunk-Idx:  {chunk_idx}")
                lines.append(f"  Chunk-Size: {data[5]}")

        elif cmd == 0x04:  # ANIMATION
            lines.append(f"Animation-Chunk-Daten: {len(data)} Bytes")
            if len(data) >= 6:
                lines.append(f"  Sequenz:    0x{data[0]:02X}")
                total = (data[1] << 8) | data[2]
                lines.append(f"  Total-Len:  {total}")
                chunk_idx = (data[3] << 8) | data[4]
                lines.append(f"  Chunk-Idx:  {chunk_idx}")
                lines.append(f"  Chunk-Size: {data[5]}")

        elif cmd == 0x0A:  # BEGIN_TRANSFER
            lines.append("Keine Daten (Transfer-Start-Signal)")

        else:
            lines.append(f"Unbekanntes Kommando, Daten: {data.hex(' ')}")

        return lines

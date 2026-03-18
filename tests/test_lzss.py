"""Tests für die LZSS-Kompression."""

from coolled.protocol.lzss import lzss_compress


class TestLzssCompress:
    def test_empty_input(self):
        """Leere Eingabe ergibt leere Ausgabe."""
        assert lzss_compress(b"") == b""

    def test_single_byte(self):
        """Ein einzelnes Byte wird als Literal kodiert."""
        result = lzss_compress(b"\x42")
        assert len(result) > 0
        # Erster Byte ist Flag-Byte, Bit 0 = 1 (Literal)
        assert result[0] & 0x01 == 0x01
        # Zweites Byte ist das Literal
        assert result[1] == 0x42

    def test_short_data(self):
        """Kurze Daten: alle Bytes als Literale."""
        data = b"ABC"
        result = lzss_compress(data)
        assert len(result) > 0
        # Flag-Byte: Bits 0-2 gesetzt (3 Literale)
        assert result[0] & 0x07 == 0x07

    def test_repeating_pattern_compresses(self):
        """Wiederholende Patterns sollten komprimiert werden."""
        # 256 mal das gleiche Byte → sollte deutlich kürzer werden
        data = bytes([0xAA] * 256)
        result = lzss_compress(data)
        assert len(result) < len(data)

    def test_long_repeating_pattern(self):
        """Langes wiederholendes Muster → hohe Kompressionsrate."""
        data = bytes([0x55] * 2048)
        result = lzss_compress(data)
        assert len(result) < len(data) // 2

    def test_alternating_pattern(self):
        """Alternierendes 2-Byte-Pattern (ab ab ab...) sollte komprimieren."""
        data = bytes([0xAA, 0xBB] * 128)
        result = lzss_compress(data)
        assert len(result) < len(data)

    def test_random_like_data_no_crash(self):
        """Pseudo-zufällige Daten: sollte nicht crashen, Output ≈ Input-Größe."""
        data = bytes(range(256))
        result = lzss_compress(data)
        assert len(result) > 0

    def test_all_zeros(self):
        """Null-Bytes sollten sehr gut komprimieren."""
        data = bytes(512)
        result = lzss_compress(data)
        assert len(result) < len(data) // 4

    def test_deterministic(self):
        """Gleicher Input ergibt gleichen Output."""
        data = b"Hello World! This is a test of LZSS compression."
        assert lzss_compress(data) == lzss_compress(data)

    def test_output_starts_with_flag_byte(self):
        """Jeder Ausgabeblock beginnt mit einem Flag-Byte."""
        data = b"Test data for LZSS"
        result = lzss_compress(data)
        assert len(result) >= 2

    def test_max_literal_block(self):
        """8 verschiedene Literale ergeben Flag-Byte 0xFF."""
        # Bytes die nicht im initialen Window (0-gefüllt) vorkommen
        data = bytes([0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80])
        result = lzss_compress(data)
        # Flag-Byte sollte 0xFF sein (alle 8 Bits = Literal)
        assert result[0] == 0xFF

    def test_large_data(self):
        """4KB Daten mit gemischten Patterns."""
        data = (bytes(range(256)) * 4 + bytes([0xFF] * 1024))
        result = lzss_compress(data)
        assert len(result) > 0
        assert len(result) < len(data)

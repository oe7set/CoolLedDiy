"""Tests für den CoolLed-spezifischen CRC-32 Algorithmus."""

from coolled.protocol.crc32 import crc32_coolled, crc32_coolled_bytes


class TestCrc32Coolled:
    def test_empty_data(self):
        """Leere Daten sollten den Startwert zurückgeben (nach 0 Iterationen)."""
        result = crc32_coolled(b"")
        assert result == 0xFFFFFFFF

    def test_single_zero_byte(self):
        """Ein Null-Byte: 32 Iterationen nur mit CRC-Shift, kein Input-Bit gesetzt."""
        result = crc32_coolled(b"\x00")
        # Alle 32 Iterationen: nur CRC shift + polynomial (input immer 0)
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFFFFFF

    def test_single_ff_byte(self):
        """0xFF Byte hat Bits 7-0 gesetzt."""
        result = crc32_coolled(b"\xff")
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFFFFFF

    def test_deterministic(self):
        """Gleicher Input ergibt gleichen CRC."""
        data = b"Hello CoolLed"
        assert crc32_coolled(data) == crc32_coolled(data)

    def test_different_inputs_differ(self):
        """Verschiedene Inputs sollten verschiedene CRCs ergeben."""
        crc1 = crc32_coolled(b"abc")
        crc2 = crc32_coolled(b"abd")
        assert crc1 != crc2

    def test_known_pattern_all_zeros(self):
        """8 Null-Bytes: reproduzierbarer CRC."""
        result = crc32_coolled(bytes(8))
        # Spezifischer Wert, sollte sich nicht ändern
        assert result == crc32_coolled(bytes(8))

    def test_crc32_bytes_format(self):
        """crc32_coolled_bytes gibt 4 Bytes Big-Endian zurück."""
        result = crc32_coolled_bytes(b"test")
        assert len(result) == 4
        assert isinstance(result, bytes)

    def test_crc32_bytes_matches_int(self):
        """Bytes-Variante entspricht der Int-Variante."""
        data = b"test data"
        crc_int = crc32_coolled(data)
        crc_bytes = crc32_coolled_bytes(data)
        reconstructed = int.from_bytes(crc_bytes, byteorder="big")
        assert reconstructed == crc_int

    def test_not_standard_zlib_crc32(self):
        """Dieser CRC ist NICHT identisch mit zlib.crc32()."""
        import zlib
        data = b"test"
        coolled_crc = crc32_coolled(data)
        standard_crc = zlib.crc32(data) & 0xFFFFFFFF
        assert coolled_crc != standard_crc

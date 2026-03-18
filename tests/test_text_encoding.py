"""Tests für die Text-Enkodierung."""

import os
from unittest.mock import MagicMock, patch

import pytest

from coolled.protocol.framing import unframe_packet
from coolled.protocol.text_encoding import _xor_checksum, encode_text_packets


class TestXorChecksum:
    def test_zeros(self):
        assert _xor_checksum(bytes([0x00, 0x00, 0x00])) == 0x00

    def test_single_byte(self):
        assert _xor_checksum(bytes([0x42])) == 0x42

    def test_xor_pairs(self):
        # 0xFF ^ 0xFF = 0x00
        assert _xor_checksum(bytes([0xFF, 0xFF])) == 0x00

    def test_known_value(self):
        # 0x01 ^ 0x02 ^ 0x03 = 0x00
        assert _xor_checksum(bytes([0x01, 0x02, 0x03])) == 0x00


class TestEncodeTextPackets:
    @pytest.fixture
    def mock_font_reader(self):
        """Erzeugt einen Mock-FontReader der bekannte Daten zurückgibt."""
        reader = MagicMock()
        # Simuliere: jedes Zeichen = 24 Bytes (UNICODE12)
        reader.read_text_12.return_value = (bytes(24), [24])
        reader.read_text_16.return_value = (bytes(32), [32])
        return reader

    def test_single_char_produces_packets(self, mock_font_reader):
        packets = encode_text_packets("A", mock_font_reader, use_font_16=False)
        assert len(packets) >= 1
        # Jedes Paket sollte ein gültiges Frame sein
        for packet in packets:
            assert packet[0] == 0x01   # FRAME_START
            assert packet[-1] == 0x03  # FRAME_END

    def test_payload_starts_with_cmd_text(self, mock_font_reader):
        packets = encode_text_packets("A", mock_font_reader)
        payload = unframe_packet(packets[0])
        assert payload[0] == 0x02  # CMD_TEXT

    def test_font_16_uses_correct_reader(self, mock_font_reader):
        encode_text_packets("X", mock_font_reader, use_font_16=True)
        mock_font_reader.read_text_16.assert_called_once_with("X")
        mock_font_reader.read_text_12.assert_not_called()

    def test_font_12_uses_correct_reader(self, mock_font_reader):
        encode_text_packets("X", mock_font_reader, use_font_16=False)
        mock_font_reader.read_text_12.assert_called_once_with("X")
        mock_font_reader.read_text_16.assert_not_called()

    def test_long_text_produces_multiple_packets(self, mock_font_reader):
        # 10 Zeichen à 24 Bytes = 240 Bytes Fontdaten
        # + 24 Header + 1 TextLen + 80 Widths + 2 DataLen = 347 Bytes
        # Bei 128-Byte-Chunks → 3 Chunks → 3 Pakete
        mock_font_reader.read_text_12.return_value = (bytes(240), [24] * 10)
        packets = encode_text_packets("ABCDEFGHIJ", mock_font_reader)
        assert len(packets) >= 2

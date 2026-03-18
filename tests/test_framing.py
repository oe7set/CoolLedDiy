"""Tests für das Paket-Framing (escape, frame, unframe)."""

from coolled.protocol.framing import (
    escape_data,
    frame_packet,
    int_to_2bytes_be,
    unescape_data,
    unframe_packet,
)


class TestInt2BytesBE:
    def test_zero(self):
        assert int_to_2bytes_be(0) == b'\x00\x00'

    def test_small(self):
        assert int_to_2bytes_be(5) == b'\x00\x05'

    def test_256(self):
        assert int_to_2bytes_be(256) == b'\x01\x00'

    def test_max(self):
        assert int_to_2bytes_be(0xFFFF) == b'\xFF\xFF'


class TestEscapeData:
    def test_no_escape_needed(self):
        data = bytes([0x00, 0x04, 0x05, 0xFF])
        assert escape_data(data) == data

    def test_escape_01(self):
        # 0x01 → [0x02, 0x01^0x04] = [0x02, 0x05]
        assert escape_data(bytes([0x01])) == bytes([0x02, 0x05])

    def test_escape_02(self):
        # 0x02 → [0x02, 0x02^0x04] = [0x02, 0x06]
        assert escape_data(bytes([0x02])) == bytes([0x02, 0x06])

    def test_escape_03(self):
        # 0x03 → [0x02, 0x03^0x04] = [0x02, 0x07]
        assert escape_data(bytes([0x03])) == bytes([0x02, 0x07])

    def test_mixed(self):
        data = bytes([0x00, 0x01, 0x04, 0x02, 0xFF])
        expected = bytes([0x00, 0x02, 0x05, 0x04, 0x02, 0x06, 0xFF])
        assert escape_data(data) == expected


class TestUnescapeData:
    def test_roundtrip(self):
        original = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0xFF])
        assert unescape_data(escape_data(original)) == original

    def test_simple_unescape(self):
        # [0x02, 0x05] → 0x01
        assert unescape_data(bytes([0x02, 0x05])) == bytes([0x01])


class TestFramePacket:
    def test_simple_command(self):
        # Payload: [0x08, 0x04] (Brightness 4)
        result = frame_packet(bytes([0x08, 0x04]))
        # Frame: START(0x01) + escaped(len_2B + payload) + END(0x03)
        # Length = 2 → [0x00, 0x02] → escaped [0x00, 0x02, 0x06]
        # Payload = [0x08, 0x04] → kein Escaping nötig
        assert result[0] == 0x01   # START
        assert result[-1] == 0x03  # END

    def test_unframe_roundtrip(self):
        payload = bytes([0x08, 0x04])
        frame = frame_packet(payload)
        recovered = unframe_packet(frame)
        assert recovered == payload

    def test_unframe_with_escape(self):
        # Payload enthält Bytes die escaped werden
        payload = bytes([0x06, 0x01])
        frame = frame_packet(payload)
        recovered = unframe_packet(frame)
        assert recovered == payload

    def test_unframe_complex(self):
        payload = bytes([0x02, 0x00, 0x01, 0x03, 0xFF])
        frame = frame_packet(payload)
        recovered = unframe_packet(frame)
        assert recovered == payload


class TestUnframePacket:
    def test_invalid_too_short(self):
        assert unframe_packet(b'\x01\x03') is None

    def test_invalid_no_start(self):
        assert unframe_packet(b'\x00\x00\x02\x08\x04\x03') is None

    def test_invalid_no_end(self):
        assert unframe_packet(b'\x01\x00\x02\x08\x04\x00') is None

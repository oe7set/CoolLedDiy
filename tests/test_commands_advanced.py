"""Tests für die erweiterten Kommando-Builder (M/U/UX-Geräte)."""

from coolled.protocol.commands_advanced import (
    build_animation_content,
    build_data_packets,
    build_draw_content,
    build_program_data,
    build_program_transfer,
    build_start_packet,
    build_text_content,
    cmd_brightness_m,
    cmd_switch_m,
)
from coolled.protocol.constants import CMD_M_BRIGHTNESS, CMD_M_DATA, CMD_M_START, CMD_M_SWITCH
from coolled.protocol.crc32 import crc32_coolled_bytes
from coolled.protocol.framing import unframe_packet


class TestBuildStartPacket:
    def test_start_packet_format(self):
        """Start-Paket: CMD_M_START + CRC(4B) + Len(4B) + Count(1B) + Show(1B)."""
        data = bytes(range(100))
        packet = build_start_packet(data, content_count=1, show_count=0)
        payload = unframe_packet(packet)

        assert payload[0] == CMD_M_START
        # CRC-32 (4 Bytes)
        expected_crc = crc32_coolled_bytes(data)
        assert payload[1:5] == expected_crc
        # Total Length (4 Bytes BE)
        expected_len = len(data).to_bytes(4, "big")
        assert payload[5:9] == expected_len
        # Content Count + Show Count
        assert payload[9] == 1
        assert payload[10] == 0

    def test_start_packet_length(self):
        """Start-Paket Payload hat immer 11 Bytes."""
        data = bytes(50)
        packet = build_start_packet(data, 2, 3)
        payload = unframe_packet(packet)
        assert len(payload) == 11


class TestBuildDataPackets:
    def test_single_chunk(self):
        """Daten ≤ 1024 Bytes → 1 Paket."""
        data = bytes(range(256)) * 2  # 512 Bytes
        packets = build_data_packets(data)
        assert len(packets) == 1

    def test_multiple_chunks(self):
        """Daten > 1024 Bytes → mehrere Pakete."""
        data = bytes(2500)
        packets = build_data_packets(data)
        assert len(packets) == 3  # ceil(2500/1024) = 3

    def test_chunk_format(self):
        """Chunk-Format: CMD_M_DATA + 0x00 + total_len(4B) + idx(2B) + size(2B) + data + XOR."""
        data = bytes(range(100))
        packets = build_data_packets(data)
        payload = unframe_packet(packets[0])

        # CMD_M_DATA
        assert payload[0] == CMD_M_DATA
        # 0x00 Marker
        assert payload[1] == 0x00
        # Total Length (4 Bytes BE)
        total_len = int.from_bytes(payload[2:6], "big")
        assert total_len == 100
        # Chunk Index (2 Bytes BE)
        chunk_idx = int.from_bytes(payload[6:8], "big")
        assert chunk_idx == 0
        # Chunk Size (2 Bytes BE)
        chunk_size = int.from_bytes(payload[8:10], "big")
        assert chunk_size == 100
        # Data
        assert payload[10:110] == data
        # XOR Checksum (letztes Byte)
        xor = 0
        for b in payload[1:-1]:  # Alles zwischen CMD und Checksum
            xor ^= b
        assert payload[-1] == xor

    def test_chunk_index_increments(self):
        """Chunk-Index zählt hoch."""
        data = bytes(2048 + 512)  # 3 Chunks
        packets = build_data_packets(data)
        for i, pkt in enumerate(packets):
            payload = unframe_packet(pkt)
            chunk_idx = int.from_bytes(payload[6:8], "big")
            assert chunk_idx == i

    def test_empty_data(self):
        """Leere Daten → keine Pakete."""
        packets = build_data_packets(b"")
        assert len(packets) == 0


class TestBuildProgramData:
    def test_program_format(self):
        """Programm-Daten: 8 Null-Bytes + Count + Show + Content."""
        content = bytes([0xAA, 0xBB, 0xCC])
        result = build_program_data(content, content_count=1, show_count=0)

        # 8 Null-Bytes Header
        assert result[:8] == bytes(8)
        # Content Count
        assert result[8] == 1
        # Show Count
        assert result[9] == 0
        # Content Data
        assert result[10:] == content

    def test_program_data_length(self):
        """Gesamtlänge = 10 + Content-Länge."""
        content = bytes(50)
        result = build_program_data(content)
        assert len(result) == 10 + 50


class TestBuildProgramTransfer:
    def test_returns_start_and_data(self):
        """build_program_transfer gibt (start_packet, data_packets) zurück."""
        program_data = bytes(100)
        start_pkt, data_pkts = build_program_transfer(program_data)

        # Start-Paket ist ein einzelnes bytes-Objekt
        assert isinstance(start_pkt, bytes)
        # Data-Pakete ist eine Liste
        assert isinstance(data_pkts, list)
        assert len(data_pkts) > 0

    def test_start_packet_has_correct_crc(self):
        """Start-Paket CRC bezieht sich auf unkomprimierte Programm-Daten."""
        program_data = bytes(range(100))
        start_pkt, _ = build_program_transfer(program_data)
        payload = unframe_packet(start_pkt)

        expected_crc = crc32_coolled_bytes(program_data)
        assert payload[1:5] == expected_crc


class TestCmdBrightnessM:
    def test_brightness_m_cmd_byte(self):
        """M/U/UX Brightness nutzt Kommando-Byte 0x04."""
        frame = cmd_brightness_m(128)
        payload = unframe_packet(frame)
        assert payload[0] == CMD_M_BRIGHTNESS
        assert payload[1] == 128

    def test_brightness_m_zero(self):
        frame = cmd_brightness_m(0)
        payload = unframe_packet(frame)
        assert payload[1] == 0

    def test_brightness_m_max(self):
        frame = cmd_brightness_m(255)
        payload = unframe_packet(frame)
        assert payload[1] == 255


class TestCmdSwitchM:
    def test_switch_m_on(self):
        """M/U/UX Switch nutzt Kommando-Byte 0x05."""
        frame = cmd_switch_m(True)
        payload = unframe_packet(frame)
        assert payload[0] == CMD_M_SWITCH
        assert payload[1] == 0x01

    def test_switch_m_off(self):
        frame = cmd_switch_m(False)
        payload = unframe_packet(frame)
        assert payload[0] == CMD_M_SWITCH
        assert payload[1] == 0x00


class TestBuildTextContent:
    def test_text_content_format(self):
        """TextContentProgramContent: Type=0x01, Header, mode/speed/stay, dataLen, data."""
        font_data = bytes([0xAA, 0xBB, 0xCC, 0xDD])
        content = build_text_content(font_data, show_width=96, show_height=16, mode=3, speed=5)

        # 4-Byte Längenprefix (Big-Endian)
        size = int.from_bytes(content[0:4], "big")
        assert size == len(content)  # size+4 inkl. Prefix

        # Content-Typ = 0x01
        assert content[4] == 0x01
        # 7 Null-Bytes Padding
        assert content[5:12] == bytes(7)
        # layerType = 0
        assert content[12] == 0
        # startCol = 0 (2B BE)
        assert content[13:15] == bytes(2)
        # startRow = 0 (2B BE)
        assert content[15:17] == bytes(2)
        # showWidth = 96 (2B BE)
        assert int.from_bytes(content[17:19], "big") == 96
        # showHeight = 16 (2B BE)
        assert int.from_bytes(content[19:21], "big") == 16
        # mode = 3
        assert content[21] == 3
        # speed = 5
        assert content[22] == 5
        # stayTime = 0
        assert content[23] == 0
        # dataLen (4B BE)
        data_len = int.from_bytes(content[24:28], "big")
        assert data_len == len(font_data)
        # font_data
        assert content[28:] == font_data

    def test_content_wrapper_length(self):
        """4-Byte Längenprefix == Gesamtlänge des Content-Blocks."""
        data = bytes(200)
        content = build_text_content(data, 128, 32)
        size = int.from_bytes(content[0:4], "big")
        assert size == len(content)


class TestBuildDrawContent:
    def test_draw_content_format(self):
        """GraffitiCombineProgram: Type=0x02, gleiche Struktur wie Text."""
        bitmap = bytes(64)
        content = build_draw_content(bitmap, show_width=48, show_height=16, mode=1, speed=2)

        size = int.from_bytes(content[0:4], "big")
        assert size == len(content)
        # Content-Typ = 0x02
        assert content[4] == 0x02
        # showWidth
        assert int.from_bytes(content[17:19], "big") == 48
        # showHeight
        assert int.from_bytes(content[19:21], "big") == 16
        # mode
        assert content[21] == 1
        # speed
        assert content[22] == 2
        # dataLen
        data_len = int.from_bytes(content[24:28], "big")
        assert data_len == 64
        # bitmap data
        assert content[28:] == bitmap


class TestBuildAnimationContent:
    def test_animation_content_format(self):
        """AnimationCombineProgram: Type=0x03, speed als 2 Bytes BE, kein mode-Byte."""
        anim = bytes(128)
        content = build_animation_content(anim, show_width=96, show_height=16, speed=150)

        size = int.from_bytes(content[0:4], "big")
        assert size == len(content)
        # Content-Typ = 0x03
        assert content[4] == 0x03
        # showWidth
        assert int.from_bytes(content[17:19], "big") == 96
        # showHeight
        assert int.from_bytes(content[19:21], "big") == 16
        # 0x00 Padding (kein mode-Byte)
        assert content[21] == 0x00
        # Speed als 2 Bytes BE
        assert int.from_bytes(content[22:24], "big") == 150
        # dataLen
        data_len = int.from_bytes(content[24:28], "big")
        assert data_len == 128
        # anim data
        assert content[28:] == anim

    def test_animation_speed_2bytes(self):
        """Speed > 255 muss korrekt als 2 Bytes enkodiert werden."""
        content = build_animation_content(bytes(10), 96, 16, speed=300)
        assert int.from_bytes(content[22:24], "big") == 300

"""Tests für die Kommando-Builder."""

from datetime import datetime

from coolled.protocol.commands import (
    cmd_animation_packets,
    cmd_begin_transfer,
    cmd_brightness,
    cmd_device_info,
    cmd_draw,
    cmd_draw_packets,
    cmd_mirror,
    cmd_mode,
    cmd_raw,
    cmd_speed,
    cmd_switch,
    cmd_sync_time,
)
from coolled.protocol.framing import unframe_packet


class TestCommands:
    def test_cmd_mode(self):
        frame = cmd_mode(1)
        payload = unframe_packet(frame)
        assert payload[0] == 0x06  # CMD_MODE
        assert payload[1] == 0x01

    def test_cmd_speed(self):
        frame = cmd_speed(5)
        payload = unframe_packet(frame)
        assert payload[0] == 0x07  # CMD_SPEED
        assert payload[1] == 0x05

    def test_cmd_brightness(self):
        frame = cmd_brightness(4)
        payload = unframe_packet(frame)
        assert payload[0] == 0x08  # CMD_BRIGHTNESS
        assert payload[1] == 0x04

    def test_cmd_switch_on(self):
        frame = cmd_switch(True)
        payload = unframe_packet(frame)
        assert payload[0] == 0x09  # CMD_SWITCH
        assert payload[1] == 0x01  # on

    def test_cmd_switch_off(self):
        frame = cmd_switch(False)
        payload = unframe_packet(frame)
        assert payload[0] == 0x09
        assert payload[1] == 0x00  # off

    def test_cmd_begin_transfer(self):
        frame = cmd_begin_transfer()
        payload = unframe_packet(frame)
        assert payload[0] == 0x0A  # CMD_BEGIN_TRANSFER

    def test_cmd_draw(self):
        bitmap = bytes([0xFF] * 96)  # 12×48 bitmap
        frame = cmd_draw(bitmap)
        payload = unframe_packet(frame)
        assert payload[0] == 0x03  # CMD_DRAW
        assert payload[1:] == bitmap

    def test_cmd_draw_packets(self):
        """cmd_draw_packets erzeugt Chunk-Pakete mit CMD_DRAW (0x03)."""
        bitmap = bytes([0xFF] * 96)
        packets = cmd_draw_packets(bitmap)
        assert len(packets) > 0
        # Erstes Paket prüfen: CMD_DRAW Header
        payload = unframe_packet(packets[0])
        assert payload[0] == 0x03  # CMD_DRAW

    def test_cmd_draw_packets_small(self):
        """Kleine Bitmap passt in einen einzelnen Chunk."""
        bitmap = bytes([0xAA] * 32)
        packets = cmd_draw_packets(bitmap)
        assert len(packets) >= 1
        payload = unframe_packet(packets[0])
        assert payload[0] == 0x03

    def test_cmd_raw(self):
        raw = bytes([0x42, 0x43])
        frame = cmd_raw(raw)
        payload = unframe_packet(frame)
        assert payload == raw

    def test_cmd_sync_time(self):
        dt = datetime(2025, 3, 15, 14, 30, 45)  # Samstag
        frame = cmd_sync_time(dt)
        payload = unframe_packet(frame)
        assert payload[0] == 0x09  # CMD_SYNC_TIME
        assert payload[1] == 25   # 2025 - 2000
        assert payload[2] == 3    # März
        assert payload[3] == 15   # Tag
        assert payload[4] == 6    # Samstag (isoweekday)
        assert payload[5] == 14   # Stunde
        assert payload[6] == 30   # Minute
        assert payload[7] == 45   # Sekunde

    def test_cmd_sync_time_default(self):
        """cmd_sync_time() ohne Parameter nutzt aktuelle Zeit."""
        frame = cmd_sync_time()
        payload = unframe_packet(frame)
        assert payload[0] == 0x09
        assert len(payload) == 8

    def test_cmd_mirror_on(self):
        frame = cmd_mirror(True)
        payload = unframe_packet(frame)
        assert payload[0] == 0x0C  # CMD_MIRROR
        assert payload[1] == 0x01

    def test_cmd_mirror_off(self):
        frame = cmd_mirror(False)
        payload = unframe_packet(frame)
        assert payload[0] == 0x0C
        assert payload[1] == 0x00

    def test_cmd_device_info(self):
        frame = cmd_device_info()
        payload = unframe_packet(frame)
        assert payload[0] == 0x1F  # CMD_DEVICE_INFO
        assert len(payload) == 1

    def test_cmd_animation_packets(self):
        # 2 Frames à 96 Bytes (12×48 Bitmap)
        frame1 = bytes([0xAA] * 96)
        frame2 = bytes([0x55] * 96)
        packets = cmd_animation_packets([frame1, frame2], speed=200)
        assert len(packets) > 0
        # Erstes Paket prüfen
        payload = unframe_packet(packets[0])
        assert payload[0] == 0x04  # CMD_ANIMATION

    def test_cmd_animation_packets_single_frame(self):
        frame = bytes([0xFF] * 32)
        packets = cmd_animation_packets([frame], speed=100)
        assert len(packets) >= 1
        payload = unframe_packet(packets[0])
        assert payload[0] == 0x04

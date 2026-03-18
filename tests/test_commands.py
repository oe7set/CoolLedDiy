"""Tests für die Kommando-Builder."""

from coolled.protocol.commands import (
    cmd_begin_transfer,
    cmd_brightness,
    cmd_draw,
    cmd_mode,
    cmd_raw,
    cmd_speed,
    cmd_switch,
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

    def test_cmd_raw(self):
        raw = bytes([0x42, 0x43])
        frame = cmd_raw(raw)
        payload = unframe_packet(frame)
        assert payload == raw

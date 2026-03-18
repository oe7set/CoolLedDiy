"""Tests für den Scan-Record Parser."""

from coolled.protocol.scan_record import ScanRecordInfo, parse_scan_record


class TestParseScanRecord:
    def _make_record(self, rows=16, cols=64, color_type=0, fw_version=4, device_id=0x1234):
        """Erzeugt einen Test-Scan-Record (31 Bytes)."""
        data = bytearray(31)
        # Device ID (Bytes 9-10)
        data[9] = (device_id >> 8) & 0xFF
        data[10] = device_id & 0xFF
        # Rows (Byte 17)
        data[17] = rows
        # Columns (Bytes 18-19, Big-Endian)
        data[18] = (cols >> 8) & 0xFF
        data[19] = cols & 0xFF
        # Color type (Byte 20)
        data[20] = color_type
        # FW version (Byte 21)
        data[21] = fw_version
        return bytes(data)

    def test_parse_16x64(self):
        data = self._make_record(rows=16, cols=64, color_type=1, fw_version=5)
        info = parse_scan_record(data)
        assert info is not None
        assert info.rows == 16
        assert info.columns == 64
        assert info.color_type == 1
        assert info.fw_version == 5

    def test_parse_32x128(self):
        data = self._make_record(rows=32, cols=128)
        info = parse_scan_record(data)
        assert info.rows == 32
        assert info.columns == 128

    def test_parse_device_id(self):
        data = self._make_record(device_id=0xABCD)
        info = parse_scan_record(data)
        assert info.device_id == 0xABCD

    def test_color_type_name(self):
        info = ScanRecordInfo(device_id=0, rows=16, columns=64, color_type=1, fw_version=0)
        assert info.color_type_name == "7-Color"

    def test_matrix_size(self):
        info = ScanRecordInfo(device_id=0, rows=16, columns=64, color_type=0, fw_version=0)
        assert info.matrix_size == "16x64"

    def test_too_short(self):
        assert parse_scan_record(bytes(10)) is None

    def test_empty(self):
        assert parse_scan_record(b'') is None

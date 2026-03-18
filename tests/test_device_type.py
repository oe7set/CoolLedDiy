"""Tests für die Gerätetyp-Erkennung."""

from coolled.protocol.device_type import (
    DeviceFamily,
    detect_device_family,
    uses_advanced_protocol,
    uses_begin_transfer,
)


class TestDetectDeviceFamily:
    """Erkennung der Gerätefamilie aus BLE-Namen."""

    # --- Light1248 Familie ---

    def test_coolled_basic(self):
        assert detect_device_family("CoolLED") == DeviceFamily.LIGHT_1248

    def test_coolled_with_suffix(self):
        assert detect_device_family("CoolLED-1234") == DeviceFamily.LIGHT_1248

    def test_coolledx(self):
        assert detect_device_family("CoolLEDX") == DeviceFamily.LIGHT_1248

    def test_coolledx_suffix(self):
        assert detect_device_family("CoolLEDX-AB12") == DeviceFamily.LIGHT_1248

    def test_coolleda(self):
        assert detect_device_family("CoolLEDA") == DeviceFamily.LIGHT_1248

    def test_coolleds(self):
        assert detect_device_family("CoolLEDS") == DeviceFamily.LIGHT_1248

    # --- Light536 Familie ---

    def test_coolled536(self):
        assert detect_device_family("CoolLED536") == DeviceFamily.LIGHT_536

    def test_coolled536_suffix(self):
        assert detect_device_family("CoolLED536-XY") == DeviceFamily.LIGHT_536

    # --- CoolledM Familie ---

    def test_coolledm(self):
        assert detect_device_family("CoolLEDM") == DeviceFamily.COOLED_M

    def test_coolledm_suffix(self):
        assert detect_device_family("CoolLEDM-1632") == DeviceFamily.COOLED_M

    # --- CoolledU Familie ---

    def test_cooledu(self):
        assert detect_device_family("CoolLEDU") == DeviceFamily.COOLED_U

    def test_cooledu_suffix(self):
        assert detect_device_family("CoolLEDU-XXXX") == DeviceFamily.COOLED_U

    def test_iledbike(self):
        """iLedBike ist ein UD-Gerät (U-Familie)."""
        assert detect_device_family("iLedBike") == DeviceFamily.COOLED_U

    def test_iledhat(self):
        assert detect_device_family("iLedHat") == DeviceFamily.COOLED_U

    def test_idevileyes(self):
        assert detect_device_family("iDevilEyes") == DeviceFamily.COOLED_U

    # --- CoolledUX Familie ---

    def test_cooledux(self):
        assert detect_device_family("CoolLEDUX") == DeviceFamily.COOLED_UX

    def test_cooledux_suffix(self):
        assert detect_device_family("CoolLEDUX-5678") == DeviceFamily.COOLED_UX

    def test_iledclock(self):
        assert detect_device_family("iLedClock") == DeviceFamily.COOLED_UX

    def test_iledopen(self):
        assert detect_device_family("iLedOpen") == DeviceFamily.COOLED_UX

    def test_iledhatc(self):
        """iLedHatC ist UX-Familie (nicht zu verwechseln mit iLedHat = U)."""
        assert detect_device_family("iLedHatC") == DeviceFamily.COOLED_UX

    # --- Priorität: UX vor U ---

    def test_ux_before_u(self):
        """CoolLEDUX muss UX sein, nicht U (obwohl UX mit U beginnt)."""
        assert detect_device_family("CoolLEDUX") == DeviceFamily.COOLED_UX

    def test_iledhatc_before_iledhat(self):
        """iLedHatC muss UX sein, nicht U (obwohl iLedHatC mit iLedHat beginnt)."""
        assert detect_device_family("iLedHatC") == DeviceFamily.COOLED_UX

    # --- Fallback ---

    def test_unknown_default(self):
        """Unbekannte Namen fallen auf LIGHT_1248 zurück."""
        assert detect_device_family("UnknownDevice") == DeviceFamily.LIGHT_1248

    def test_empty_name(self):
        assert detect_device_family("") == DeviceFamily.LIGHT_1248


class TestUsesAdvancedProtocol:
    def test_light1248_not_advanced(self):
        assert not uses_advanced_protocol(DeviceFamily.LIGHT_1248)

    def test_light536_not_advanced(self):
        assert not uses_advanced_protocol(DeviceFamily.LIGHT_536)

    def test_cooled_m_advanced(self):
        assert uses_advanced_protocol(DeviceFamily.COOLED_M)

    def test_cooled_u_advanced(self):
        assert uses_advanced_protocol(DeviceFamily.COOLED_U)

    def test_cooled_ux_advanced(self):
        assert uses_advanced_protocol(DeviceFamily.COOLED_UX)


class TestUsesBeginTransfer:
    def test_light1248_no_begin(self):
        """Light1248 sendet Text/Draw direkt ohne begin_transfer."""
        assert not uses_begin_transfer(DeviceFamily.LIGHT_1248)

    def test_light536_uses_begin(self):
        """Light536 braucht begin_transfer + 50ms Delay."""
        assert uses_begin_transfer(DeviceFamily.LIGHT_536)

    def test_cooled_m_no_begin(self):
        """M/U/UX nutzen Programm-Format, kein begin_transfer."""
        assert not uses_begin_transfer(DeviceFamily.COOLED_M)

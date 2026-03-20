"""Tests für den RGB444-Konverter (CoolLedUX-Pixelformat)."""

from PIL import Image

from coolled.image.converter import image_to_rgb444, rgb444_transfer


class TestRgb444Transfer:
    def test_zero(self):
        """Werte <= 47 ergeben 0."""
        assert rgb444_transfer(0) == 0
        assert rgb444_transfer(47) == 0

    def test_max(self):
        """Werte >= 238 ergeben 15."""
        assert rgb444_transfer(238) == 15
        assert rgb444_transfer(255) == 15

    def test_mid_range(self):
        """Mittlere Werte werden korrekt skaliert."""
        # (128 - 47) / 14 + 1 = 81/14 + 1 = 5 + 1 = 6
        assert rgb444_transfer(128) == 6

    def test_boundary_48(self):
        """Erster Wert > 47 ergibt 1."""
        assert rgb444_transfer(48) == 1


class TestImageToRgb444:
    def test_single_white_pixel(self):
        """Weißes Pixel → R=15, G=15, B=15."""
        img = Image.new("RGB", (1, 1), (255, 255, 255))
        data = image_to_rgb444(img, 1, 1)
        assert len(data) == 2
        assert data[0] == 15           # R
        assert data[1] == (15 << 4) | 15  # G<<4 | B = 0xFF

    def test_single_black_pixel(self):
        """Schwarzes Pixel → R=0, G=0, B=0."""
        img = Image.new("RGB", (1, 1), (0, 0, 0))
        data = image_to_rgb444(img, 1, 1)
        assert data[0] == 0
        assert data[1] == 0

    def test_red_pixel(self):
        """Rotes Pixel → R=15, G=0, B=0."""
        img = Image.new("RGB", (1, 1), (255, 0, 0))
        data = image_to_rgb444(img, 1, 1)
        assert data[0] == 15
        assert data[1] == 0

    def test_green_pixel(self):
        """Gruenes Pixel → R=0, G=15, B=0."""
        img = Image.new("RGB", (1, 1), (0, 255, 0))
        data = image_to_rgb444(img, 1, 1)
        assert data[0] == 0
        assert data[1] == (15 << 4) | 0  # 0xF0

    def test_blue_pixel(self):
        """Blaues Pixel → R=0, G=0, B=15."""
        img = Image.new("RGB", (1, 1), (0, 0, 255))
        data = image_to_rgb444(img, 1, 1)
        assert data[0] == 0
        assert data[1] == 15  # 0x0F

    def test_output_length(self):
        """Ausgabelaenge = width * height * 2."""
        img = Image.new("RGB", (64, 16), (128, 128, 128))
        data = image_to_rgb444(img, 64, 16)
        assert len(data) == 64 * 16 * 2

    def test_column_major_order(self):
        """Daten sind Column-major: erst alle Zeilen von Spalte 0, dann Spalte 1, etc."""
        img = Image.new("RGB", (2, 2), (0, 0, 0))
        img.putpixel((0, 0), (255, 0, 0))    # x=0,y=0 → rot
        img.putpixel((0, 1), (0, 255, 0))    # x=0,y=1 → gruen
        img.putpixel((1, 0), (0, 0, 255))    # x=1,y=0 → blau
        img.putpixel((1, 1), (255, 255, 255))  # x=1,y=1 → weiss

        data = image_to_rgb444(img, 2, 2)
        # Column 0: (0,0)=rot, (0,1)=gruen
        assert data[0] == 15   # R rot
        assert data[1] == 0    # GB rot
        assert data[2] == 0    # R gruen
        assert data[3] == 0xF0  # G gruen
        # Column 1: (1,0)=blau, (1,1)=weiss
        assert data[4] == 0    # R blau
        assert data[5] == 0x0F  # B blau
        assert data[6] == 15   # R weiss
        assert data[7] == 0xFF  # GB weiss

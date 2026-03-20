"""
Bild-zu-Bitmap-Konverter für CoolLed LED-Matrix-Panels.

Konvertiert Bilder (via Pillow) in das spaltenweise Bitmap-Format des Panels.
Basiert auf Light1248Utils.java:163-196 (getDrawListData).

Column-Encoding für 12×48 Panel:
  - Pro Spalte (0..47): 2 Bytes
  - Byte 0: Top 8 Rows (MSB = Row 0, Bit=1 → LED an)
  - Byte 1: Bottom 4 Rows (gleiche Logik, obere 4 Bits)
  - Total: 96 Bytes

Für 16×N Panels: 2 Bytes pro Spalte (8+8 Rows).
"""

from PIL import Image


def load_image(path: str) -> Image.Image:
    """Lädt ein Bild von der Festplatte."""
    return Image.open(path)


def resize_to_panel(image: Image.Image, rows: int, columns: int) -> Image.Image:
    """Skaliert ein Bild auf die Panel-Größe.

    Behält das Seitenverhältnis bei und zentriert das Ergebnis auf schwarzem Hintergrund.

    Args:
        image: Eingabe-Bild
        rows: Anzahl Zeilen des Panels (Höhe)
        columns: Anzahl Spalten des Panels (Breite)

    Returns:
        Skaliertes Bild in Panel-Größe
    """
    # Seitenverhältnis berechnen
    img_ratio = image.width / image.height
    panel_ratio = columns / rows

    if img_ratio > panel_ratio:
        # Bild ist breiter → an Breite anpassen
        new_width = columns
        new_height = max(1, int(columns / img_ratio))
    else:
        # Bild ist höher → an Höhe anpassen
        new_height = rows
        new_width = max(1, int(rows * img_ratio))

    # Bild skalieren
    resized = image.resize((new_width, new_height), Image.Resampling.NEAREST)

    # Auf Panel-Größe zentrieren (schwarzer Hintergrund)
    result = Image.new("L", (columns, rows), 0)
    x_offset = (columns - new_width) // 2
    y_offset = (rows - new_height) // 2
    result.paste(resized.convert("L"), (x_offset, y_offset))

    return result


def image_to_bitmap(image: Image.Image, rows: int, threshold: int = 128) -> bytes:
    """Konvertiert ein Bild in das spaltenweise Bitmap-Format des Panels.

    Entspricht getDrawListData() in Light1248Utils.java:163-196.

    Encoding:
      Pro Spalte werden die Zeilen in Gruppen zu 8 Bits zusammengefasst.
      MSB = oberste Zeile der Gruppe, Bit=1 → LED an (Pixel dunkel genug).

    Args:
        image: Eingabe-Bild (sollte bereits auf Panel-Größe skaliert sein)
        rows: Anzahl Zeilen des Panels
        threshold: Helligkeitsschwelle (0-255), Pixel <= threshold → LED an

    Returns:
        Bitmap-Daten im Column-Encoding Format
    """
    # Bild in Graustufen konvertieren
    gray = image.convert("L")
    pixels = gray.load()
    width, height = gray.size

    # Anzahl Byte-Gruppen pro Spalte (ceil(rows / 8))
    bytes_per_column = (rows + 7) // 8

    result = bytearray()

    for col in range(width):
        for byte_group in range(bytes_per_column):
            # Wie viele Bits hat diese Gruppe? (letzte Gruppe kann weniger als 8 haben)
            start_row = byte_group * 8
            bits_in_group = min(8, rows - start_row)

            byte_val = 0
            for bit in range(bits_in_group):
                row = start_row + bit
                if row < height and col < width:
                    pixel = pixels[col, row]
                    # LED an wenn Pixel dunkel genug (unter/gleich Schwelle)
                    if pixel <= threshold:
                        byte_val |= (1 << (7 - bit))

            result.append(byte_val)

    return bytes(result)


def rgb444_transfer(value: int) -> int:
    """Konvertiert einen 8-Bit Farbkanal (0-255) in 4-Bit RGB444 (0-15).

    Entspricht rgb444Transfer() im ESP32-Referenzcode und
    TextEmojiManagerCoolLEDUX.getColorDataWithColorWithRGB444Transfer() in der Android-App.
    """
    if value >= 238:
        return 15
    if value <= 47:
        return 0
    return ((value - 47) // 14) + 1


def image_to_rgb444(image: Image.Image, width: int, height: int) -> bytes:
    """Konvertiert ein Bild in RGB444-Pixeldaten für CoolLedUX-Geräte.

    Column-major Reihenfolge: für jede Spalte x, für jede Zeile y.
    Pro Pixel 2 Bytes: [R_4bit, (G_4bit << 4) | B_4bit].

    Basiert auf getDrawListDataFColor() in CoolledUXUtils.java und dem
    funktionierenden ESP32-Referenzcode (setPixel/buildProgramData).

    Args:
        image: Eingabe-Bild (sollte bereits auf Panel-Größe skaliert sein)
        width: Panel-Breite in Pixeln (Spalten)
        height: Panel-Höhe in Pixeln (Zeilen)

    Returns:
        RGB444-Pixeldaten (Länge = width * height * 2)
    """
    rgb = image.convert("RGB")
    pixels = rgb.load()

    result = bytearray()
    for x in range(width):
        for y in range(height):
            r, g, b = pixels[x, y]
            result.append(rgb444_transfer(r))
            result.append((rgb444_transfer(g) << 4) | rgb444_transfer(b))

    return bytes(result)


def bitmap_to_image(bitmap: bytes, rows: int, columns: int) -> Image.Image:
    """Konvertiert Bitmap-Daten zurück in ein Bild (für Preview).

    Umkehrung von image_to_bitmap() - nützlich für die LED-Vorschau.

    Args:
        bitmap: Bitmap-Daten im Column-Encoding Format
        rows: Anzahl Zeilen des Panels
        columns: Anzahl Spalten des Panels

    Returns:
        Schwarz-weiß Bild der Bitmap-Daten
    """
    bytes_per_column = (rows + 7) // 8
    image = Image.new("L", (columns, rows), 0)
    pixels = image.load()

    for col in range(columns):
        for byte_group in range(bytes_per_column):
            byte_index = col * bytes_per_column + byte_group
            if byte_index >= len(bitmap):
                break

            byte_val = bitmap[byte_index]
            start_row = byte_group * 8
            bits_in_group = min(8, rows - start_row)

            for bit in range(bits_in_group):
                row = start_row + bit
                if byte_val & (1 << (7 - bit)):
                    pixels[col, row] = 255  # LED an → weiß in Preview

    return image

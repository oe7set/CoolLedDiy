"""
Bild-Sender Tab - Bilder an CoolLed Panel senden.

Enthält:
- Load-Button zum Laden eines Bildes
- Original-Vorschau und Panel-Vorschau
- Threshold-Slider für Schwarz/Weiß-Konvertierung
- Send-Button
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PIL import Image

from coolled.gui.widgets.led_preview import LedPreview
from coolled.image.converter import image_to_bitmap, resize_to_panel


class ImageTab(QWidget):
    """Tab zum Senden von Bildern an das CoolLed Panel."""

    # Signal mit den zu sendenden Bitmap-Daten
    send_image_requested = Signal(bytes)  # bitmap_data

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._image: Image.Image | None = None
        self._rows = 16
        self._columns = 64
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Panel-Größe
        size_group = QGroupBox("Panel-Größe")
        size_layout = QHBoxLayout(size_group)
        size_layout.addWidget(QLabel("Zeilen:"))
        self._rows_spin = QSpinBox()
        self._rows_spin.setRange(8, 64)
        self._rows_spin.setValue(16)
        self._rows_spin.valueChanged.connect(self._on_size_changed)
        size_layout.addWidget(self._rows_spin)
        size_layout.addWidget(QLabel("Spalten:"))
        self._cols_spin = QSpinBox()
        self._cols_spin.setRange(8, 512)
        self._cols_spin.setValue(64)
        self._cols_spin.valueChanged.connect(self._on_size_changed)
        size_layout.addWidget(self._cols_spin)
        size_layout.addStretch()
        layout.addWidget(size_group)

        # Bild laden
        load_layout = QHBoxLayout()
        self._load_btn = QPushButton("Bild laden...")
        self._load_btn.clicked.connect(self._on_load_clicked)
        load_layout.addWidget(self._load_btn)
        self._file_label = QLabel("Kein Bild geladen")
        load_layout.addWidget(self._file_label)
        load_layout.addStretch()
        layout.addLayout(load_layout)

        # Vorschauen nebeneinander
        previews = QHBoxLayout()

        # Original-Vorschau
        orig_group = QGroupBox("Original")
        orig_layout = QVBoxLayout(orig_group)
        self._original_label = QLabel()
        self._original_label.setMinimumSize(200, 100)
        self._original_label.setStyleSheet("background-color: #1e1e1e;")
        self._original_label.setScaledContents(True)
        orig_layout.addWidget(self._original_label)
        previews.addWidget(orig_group)

        # Panel-Vorschau (LED-Preview)
        panel_group = QGroupBox("Panel-Vorschau")
        panel_layout = QVBoxLayout(panel_group)
        self._preview = LedPreview(rows=16, columns=64)
        self._preview.setMinimumHeight(120)
        panel_layout.addWidget(self._preview)
        previews.addWidget(panel_group)

        layout.addLayout(previews)

        # Threshold-Slider
        thresh_layout = QHBoxLayout()
        thresh_layout.addWidget(QLabel("Schwelle:"))
        self._threshold_slider = QSlider()
        self._threshold_slider.setOrientation(Qt.Orientation.Horizontal)
        self._threshold_slider.setRange(0, 255)
        self._threshold_slider.setValue(128)
        self._threshold_slider.valueChanged.connect(self._on_threshold_changed)
        thresh_layout.addWidget(self._threshold_slider)
        self._threshold_label = QLabel("128")
        thresh_layout.addWidget(self._threshold_label)
        layout.addLayout(thresh_layout)

        # Senden
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._send_btn = QPushButton("Bild senden")
        self._send_btn.setEnabled(False)
        self._send_btn.clicked.connect(self._on_send_clicked)
        btn_layout.addWidget(self._send_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _on_load_clicked(self) -> None:
        """Öffnet einen Datei-Dialog zum Laden eines Bildes."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Bild laden",
            "", "Bilder (*.png *.jpg *.jpeg *.bmp *.gif);;Alle Dateien (*)"
        )
        if path:
            try:
                self._image = Image.open(path)
                self._file_label.setText(path.split("/")[-1].split("\\")[-1])
                self._update_previews()
                self._send_btn.setEnabled(True)
            except Exception as e:
                self._file_label.setText(f"Fehler: {e}")

    def _on_size_changed(self) -> None:
        """Aktualisiert die Panel-Größe und Vorschauen."""
        self._rows = self._rows_spin.value()
        self._columns = self._cols_spin.value()
        self._preview.set_size(self._rows, self._columns)
        if self._image:
            self._update_previews()

    def _on_threshold_changed(self, value: int) -> None:
        """Aktualisiert die Vorschau bei Schwellwert-Änderung."""
        self._threshold_label.setText(str(value))
        if self._image:
            self._update_previews()

    def _update_previews(self) -> None:
        """Aktualisiert Original- und Panel-Vorschau."""
        if not self._image:
            return

        # Original-Vorschau als QPixmap
        img = self._image.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
        self._original_label.setPixmap(QPixmap.fromImage(qimg))

        # Panel-Vorschau
        resized = resize_to_panel(self._image, self._rows, self._columns)
        threshold = self._threshold_slider.value()
        bitmap = image_to_bitmap(resized, self._rows, threshold=threshold)
        self._preview.set_bitmap(bitmap)

    def _on_send_clicked(self) -> None:
        """Sendet das konvertierte Bild."""
        if not self._image:
            return

        resized = resize_to_panel(self._image, self._rows, self._columns)
        threshold = self._threshold_slider.value()
        bitmap = image_to_bitmap(resized, self._rows, threshold=threshold)
        self.send_image_requested.emit(bitmap)

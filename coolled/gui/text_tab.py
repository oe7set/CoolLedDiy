"""
Text-Sender Tab - Text an CoolLed Panel senden.

Enthält:
- Text-Eingabefeld
- Font-Auswahl (UNICODE12 / UNICODE16)
- Mode/Speed/Brightness Controls
- LED-Preview des gerenderten Texts
- Send-Button
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from coolled.fonts.font_reader import FontReader
from coolled.gui.widgets.led_preview import LedPreview
from coolled.image.converter import bitmap_to_image
from coolled.protocol.constants import MODE_NAMES


class TextTab(QWidget):
    """Tab zum Senden von Text an das CoolLed Panel."""

    # Signal mit den zu sendenden Text-Paketen
    send_text_requested = Signal(str, bool)  # (text, use_font_16)

    def __init__(self, font_reader: FontReader, parent: QWidget | None = None):
        super().__init__(parent)
        self._font_reader = font_reader
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Text-Eingabe
        text_group = QGroupBox("Text eingeben")
        text_layout = QVBoxLayout(text_group)

        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText("Text hier eingeben...")
        self._text_edit.setMaximumHeight(100)
        self._text_edit.textChanged.connect(self._on_text_changed)
        text_layout.addWidget(self._text_edit)

        # Font-Auswahl
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font:"))
        self._font_combo = QComboBox()
        self._font_combo.addItem("UNICODE12 (12 Zeilen)", False)
        self._font_combo.addItem("UNICODE16 (16 Zeilen)", True)
        self._font_combo.currentIndexChanged.connect(self._on_text_changed)
        font_layout.addWidget(self._font_combo)
        font_layout.addStretch()
        text_layout.addLayout(font_layout)

        layout.addWidget(text_group)

        # LED-Vorschau
        preview_group = QGroupBox("LED-Vorschau")
        preview_layout = QVBoxLayout(preview_group)
        self._preview = LedPreview(rows=16, columns=64)
        self._preview.setMinimumHeight(120)
        preview_layout.addWidget(self._preview)
        layout.addWidget(preview_group)

        # Display-Einstellungen
        settings_group = QGroupBox("Display-Einstellungen")
        settings_layout = QVBoxLayout(settings_group)

        # Modus
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Modus:"))
        self._mode_combo = QComboBox()
        for mode_id, mode_name in MODE_NAMES.items():
            self._mode_combo.addItem(mode_name, mode_id)
        mode_layout.addWidget(self._mode_combo)
        mode_layout.addStretch()
        settings_layout.addLayout(mode_layout)

        # Geschwindigkeit
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Geschwindigkeit:"))
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(0, 255)
        self._speed_slider.setValue(127)
        speed_layout.addWidget(self._speed_slider)
        self._speed_label = QLabel("127")
        self._speed_slider.valueChanged.connect(
            lambda v: self._speed_label.setText(str(v))
        )
        speed_layout.addWidget(self._speed_label)
        settings_layout.addLayout(speed_layout)

        layout.addWidget(settings_group)

        # Senden
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._send_btn = QPushButton("Text senden")
        self._send_btn.clicked.connect(self._on_send_clicked)
        btn_layout.addWidget(self._send_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _on_text_changed(self) -> None:
        """Aktualisiert die LED-Vorschau wenn sich der Text ändert."""
        text = self._text_edit.toPlainText()
        if not text:
            self._preview.clear()
            return

        use_font_16 = self._font_combo.currentData()
        preview_rows = 16 if use_font_16 else 12

        # Preview-Zeilen an gewählten Font anpassen
        if self._preview.rows != preview_rows:
            self._preview.set_size(preview_rows, self._preview.columns)

        try:
            if use_font_16:
                font_data, widths = self._font_reader.read_text_16(text)
            else:
                font_data, widths = self._font_reader.read_text_12(text)

            # Font-Daten als Bitmap in Preview anzeigen
            self._preview.set_bitmap(font_data, preview_rows)
        except Exception:
            self._preview.clear()

    def _on_send_clicked(self) -> None:
        """Sendet den eingegebenen Text."""
        text = self._text_edit.toPlainText()
        if text:
            use_font_16 = self._font_combo.currentData()
            self.send_text_requested.emit(text, use_font_16)

    @property
    def selected_mode(self) -> int:
        """Gibt den aktuell ausgewählten Display-Modus zurück."""
        return self._mode_combo.currentData()

    @property
    def selected_speed(self) -> int:
        """Gibt die aktuell eingestellte Geschwindigkeit zurück."""
        return self._speed_slider.value()

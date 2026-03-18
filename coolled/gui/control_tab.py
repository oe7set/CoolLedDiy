"""
Quick Controls Tab - Schnellzugriff auf Display-Steuerung.

Enthält:
- Ein/Aus Schalter
- Brightness-Slider
- Speed-Slider
- Mode-Dropdown
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from coolled.protocol.constants import MODE_NAMES


class ControlTab(QWidget):
    """Tab für schnelle Display-Steuerung ohne Text/Bild-Eingabe."""

    # Signals für einzelne Steuerkommandos
    switch_requested = Signal(bool)       # Ein/Aus
    brightness_requested = Signal(int)    # 0-255
    speed_requested = Signal(int)         # 0-7
    mode_requested = Signal(int)          # Mode-ID

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._is_on = True
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Ein/Aus
        power_group = QGroupBox("Power")
        power_layout = QHBoxLayout(power_group)
        self._power_btn = QPushButton("Ausschalten")
        self._power_btn.setCheckable(True)
        self._power_btn.clicked.connect(self._on_power_clicked)
        power_layout.addWidget(self._power_btn)
        self._power_status = QLabel("Display: EIN")
        power_layout.addWidget(self._power_status)
        power_layout.addStretch()
        layout.addWidget(power_group)

        # Helligkeit
        bright_group = QGroupBox("Helligkeit")
        bright_layout = QHBoxLayout(bright_group)
        self._bright_slider = QSlider()
        self._bright_slider.setOrientation(Qt.Orientation.Horizontal)
        self._bright_slider.setRange(0, 7)
        self._bright_slider.setValue(4)
        bright_layout.addWidget(self._bright_slider)
        self._bright_label = QLabel("4")
        self._bright_slider.valueChanged.connect(
            lambda v: self._bright_label.setText(str(v))
        )
        bright_layout.addWidget(self._bright_label)
        self._bright_send_btn = QPushButton("Senden")
        self._bright_send_btn.clicked.connect(
            lambda: self.brightness_requested.emit(self._bright_slider.value())
        )
        bright_layout.addWidget(self._bright_send_btn)
        layout.addWidget(bright_group)

        # Geschwindigkeit
        speed_group = QGroupBox("Geschwindigkeit")
        speed_layout = QHBoxLayout(speed_group)
        self._speed_slider = QSlider()
        self._speed_slider.setOrientation(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(0, 7)
        self._speed_slider.setValue(3)
        speed_layout.addWidget(self._speed_slider)
        self._speed_label = QLabel("3")
        self._speed_slider.valueChanged.connect(
            lambda v: self._speed_label.setText(str(v))
        )
        speed_layout.addWidget(self._speed_label)
        self._speed_send_btn = QPushButton("Senden")
        self._speed_send_btn.clicked.connect(
            lambda: self.speed_requested.emit(self._speed_slider.value())
        )
        speed_layout.addWidget(self._speed_send_btn)
        layout.addWidget(speed_group)

        # Display-Modus
        mode_group = QGroupBox("Display-Modus")
        mode_layout = QHBoxLayout(mode_group)
        self._mode_combo = QComboBox()
        for mode_id, mode_name in MODE_NAMES.items():
            self._mode_combo.addItem(mode_name, mode_id)
        mode_layout.addWidget(self._mode_combo)
        self._mode_send_btn = QPushButton("Senden")
        self._mode_send_btn.clicked.connect(
            lambda: self.mode_requested.emit(self._mode_combo.currentData())
        )
        mode_layout.addWidget(self._mode_send_btn)
        mode_layout.addStretch()
        layout.addWidget(mode_group)

        layout.addStretch()

    def _on_power_clicked(self) -> None:
        """Schaltet das Display ein/aus."""
        self._is_on = not self._is_on
        self._power_btn.setText("Einschalten" if not self._is_on else "Ausschalten")
        self._power_status.setText(f"Display: {'EIN' if self._is_on else 'AUS'}")
        self.switch_requested.emit(self._is_on)

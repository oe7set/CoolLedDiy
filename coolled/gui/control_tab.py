"""
Quick Controls Tab - Schnellzugriff auf Display-Steuerung.

Enthält:
- Ein/Aus Schalter
- Brightness-Slider
- Speed-Slider
- Mode-Dropdown
"""

from PySide6.QtCore import Qt, QTimer, Signal
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

from coolled.protocol.constants import MODE_NAMES


class ControlTab(QWidget):
    """Tab für schnelle Display-Steuerung ohne Text/Bild-Eingabe."""

    # Signals für einzelne Steuerkommandos
    switch_requested = Signal(bool)       # Ein/Aus
    brightness_requested = Signal(int)    # 0-255
    speed_requested = Signal(int)         # 0-255
    mode_requested = Signal(int)          # Mode-ID
    sync_time_requested = Signal()        # Zeit synchronisieren
    mirror_requested = Signal(bool)       # Spiegelung Ein/Aus
    device_info_requested = Signal()      # Geräteinformation abfragen

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
        self._bright_slider.setRange(0, 255)
        self._bright_slider.setValue(255)
        bright_layout.addWidget(self._bright_slider)
        self._bright_label = QLabel("255")
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
        self._speed_slider.setRange(0, 255)
        self._speed_slider.setValue(127)
        speed_layout.addWidget(self._speed_slider)
        self._speed_label = QLabel("127")
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

        # Zeitsynchronisation
        time_group = QGroupBox("Zeitsynchronisation")
        time_layout = QHBoxLayout(time_group)
        self._sync_time_btn = QPushButton("Zeit synchronisieren")
        self._sync_time_btn.clicked.connect(self.sync_time_requested.emit)
        time_layout.addWidget(self._sync_time_btn)
        self._time_label = QLabel("")
        time_layout.addWidget(self._time_label)
        time_layout.addStretch()
        layout.addWidget(time_group)

        # Live-Uhr aktualisieren
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

        # Spiegelung
        mirror_group = QGroupBox("Spiegelung")
        mirror_layout = QHBoxLayout(mirror_group)
        self._mirror_btn = QPushButton("Spiegeln")
        self._mirror_btn.setCheckable(True)
        self._mirror_btn.clicked.connect(self._on_mirror_clicked)
        mirror_layout.addWidget(self._mirror_btn)
        self._mirror_label = QLabel("Gespiegelt: Nein")
        mirror_layout.addWidget(self._mirror_label)
        mirror_layout.addStretch()
        layout.addWidget(mirror_group)

        # Geräteinformation
        info_group = QGroupBox("Geräteinformation")
        info_layout = QVBoxLayout(info_group)
        self._info_btn = QPushButton("Geräteinformation abfragen")
        self._info_btn.clicked.connect(self.device_info_requested.emit)
        info_layout.addWidget(self._info_btn)
        self._info_display = QTextEdit()
        self._info_display.setReadOnly(True)
        self._info_display.setMaximumHeight(80)
        self._info_display.setPlaceholderText("Noch keine Geräteinformation abgefragt...")
        info_layout.addWidget(self._info_display)
        layout.addWidget(info_group)

        layout.addStretch()

    def _update_clock(self) -> None:
        """Aktualisiert die Uhrzeit-Anzeige."""
        from datetime import datetime
        now = datetime.now()
        self._time_label.setText(now.strftime("PC-Zeit: %H:%M:%S"))

    def _on_mirror_clicked(self) -> None:
        """Spiegelung ein/ausschalten."""
        mirrored = self._mirror_btn.isChecked()
        self._mirror_label.setText(f"Gespiegelt: {'Ja' if mirrored else 'Nein'}")
        self.mirror_requested.emit(mirrored)

    def set_device_info(self, info_text: str) -> None:
        """Zeigt empfangene Geräteinformation an."""
        self._info_display.setPlainText(info_text)

    def _on_power_clicked(self) -> None:
        """Schaltet das Display ein/aus."""
        self._is_on = not self._is_on
        self._power_btn.setText("Einschalten" if not self._is_on else "Ausschalten")
        self._power_status.setText(f"Display: {'EIN' if self._is_on else 'AUS'}")
        self.switch_requested.emit(self._is_on)

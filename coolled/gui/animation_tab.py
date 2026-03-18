"""
Animation Tab - Multi-Frame-Animation erstellen und an das Panel senden.

Enthält:
- Frame-Liste mit Thumbnails
- Frame-Management (Neu, Bild laden, Duplizieren, Entfernen, Sortieren)
- DrawingGrid zum Bearbeiten des aktiven Frames
- LED-Vorschau mit Play/Stop
- Geschwindigkeitsregler
"""

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from coolled.gui.widgets.drawing_grid import DrawingGrid
from coolled.gui.widgets.led_preview import LedPreview
from coolled.image.converter import image_to_bitmap, load_image, resize_to_panel


class AnimationTab(QWidget):
    """Tab zum Erstellen und Senden von Multi-Frame-Animationen."""

    # Signal: (Liste von Bitmap-Daten pro Frame, Geschwindigkeit in ms)
    send_animation_requested = Signal(list, int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        # Interner Frame-Speicher: Liste von Matrizen (list[list[bool]])
        self._frames: list[list[list[bool]]] = []
        self._current_frame: int = -1
        self._playing = False

        self._setup_ui()
        self._connect_signals()

        # Play-Timer
        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._on_play_tick)

        # Ersten leeren Frame hinzufügen
        self._add_blank_frame()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Panel-Größe (oben)
        size_layout = QHBoxLayout()
        size_group = QGroupBox("Panel-Größe")
        sg_layout = QHBoxLayout(size_group)
        sg_layout.addWidget(QLabel("Zeilen:"))
        self._rows_spin = QSpinBox()
        self._rows_spin.setRange(8, 64)
        self._rows_spin.setValue(16)
        sg_layout.addWidget(self._rows_spin)
        sg_layout.addWidget(QLabel("Spalten:"))
        self._cols_spin = QSpinBox()
        self._cols_spin.setRange(8, 256)
        self._cols_spin.setValue(64)
        sg_layout.addWidget(self._cols_spin)
        size_layout.addWidget(size_group)
        size_layout.addStretch()
        layout.addLayout(size_layout)

        # Hauptbereich: Frame-Liste | DrawingGrid | Vorschau+Controls
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Links: Frame-Liste
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("Frames:"))
        self._frame_list = QListWidget()
        self._frame_list.setIconSize(self._frame_list.iconSize())
        self._frame_list.setMinimumWidth(140)
        left_layout.addWidget(self._frame_list)

        # Frame-Buttons
        btn_layout = QVBoxLayout()
        self._btn_new = QPushButton("Neu (leer)")
        self._btn_load = QPushButton("Bild laden")
        self._btn_dup = QPushButton("Duplizieren")
        self._btn_remove = QPushButton("Entfernen")
        self._btn_up = QPushButton("Hoch")
        self._btn_down = QPushButton("Runter")
        for btn in [self._btn_new, self._btn_load, self._btn_dup,
                     self._btn_remove, self._btn_up, self._btn_down]:
            btn_layout.addWidget(btn)
        left_layout.addLayout(btn_layout)
        main_splitter.addWidget(left_panel)

        # Mitte: DrawingGrid
        self._grid = DrawingGrid(16, 64)
        main_splitter.addWidget(self._grid)

        # Rechts: Vorschau + Controls
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # LED-Vorschau
        preview_group = QGroupBox("LED-Vorschau")
        pv_layout = QVBoxLayout(preview_group)
        self._preview = LedPreview(16, 64)
        self._preview.setMinimumHeight(80)
        pv_layout.addWidget(self._preview)
        right_layout.addWidget(preview_group)

        # Geschwindigkeit
        speed_group = QGroupBox("Geschwindigkeit")
        sp_layout = QHBoxLayout(speed_group)
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(50, 2000)
        self._speed_slider.setValue(200)
        sp_layout.addWidget(self._speed_slider)
        self._speed_label = QLabel("200 ms")
        self._speed_slider.valueChanged.connect(
            lambda v: self._speed_label.setText(f"{v} ms")
        )
        sp_layout.addWidget(self._speed_label)
        right_layout.addWidget(speed_group)

        # Play/Stop + Senden
        self._play_btn = QPushButton("Vorschau abspielen")
        self._play_btn.setCheckable(True)
        right_layout.addWidget(self._play_btn)

        self._send_btn = QPushButton("Animation senden")
        self._send_btn.setMinimumHeight(36)
        right_layout.addWidget(self._send_btn)

        right_layout.addStretch()
        main_splitter.addWidget(right_panel)

        # Splitter-Proportionen: Liste 1 : Grid 3 : Controls 1
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)
        main_splitter.setStretchFactor(2, 1)
        layout.addWidget(main_splitter)

    def _connect_signals(self) -> None:
        # Frame-Auswahl
        self._frame_list.currentRowChanged.connect(self._on_frame_selected)

        # Frame-Buttons
        self._btn_new.clicked.connect(self._add_blank_frame)
        self._btn_load.clicked.connect(self._load_image_frame)
        self._btn_dup.clicked.connect(self._duplicate_frame)
        self._btn_remove.clicked.connect(self._remove_frame)
        self._btn_up.clicked.connect(self._move_frame_up)
        self._btn_down.clicked.connect(self._move_frame_down)

        # Grid-Änderung → Frame speichern + Vorschau
        self._grid.grid_changed.connect(self._on_grid_changed)

        # Panel-Größe
        self._rows_spin.valueChanged.connect(self._on_size_changed)
        self._cols_spin.valueChanged.connect(self._on_size_changed)

        # Play/Stop
        self._play_btn.clicked.connect(self._on_play_toggled)

        # Senden
        self._send_btn.clicked.connect(self._on_send)

    # --- Frame-Management ---

    def _rows(self) -> int:
        return self._rows_spin.value()

    def _cols(self) -> int:
        return self._cols_spin.value()

    def _blank_matrix(self) -> list[list[bool]]:
        """Erzeugt eine leere Matrix in aktueller Panel-Größe."""
        return [[False] * self._cols() for _ in range(self._rows())]

    def _add_blank_frame(self) -> None:
        """Fügt einen leeren Frame hinzu."""
        matrix = self._blank_matrix()
        self._frames.append(matrix)
        self._frame_list.addItem(f"Frame {len(self._frames)}")
        self._frame_list.setCurrentRow(len(self._frames) - 1)
        self._update_thumbnail(len(self._frames) - 1)

    def _load_image_frame(self) -> None:
        """Lädt ein Bild als neuen Frame."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Bild laden", "",
            "Bilder (*.png *.jpg *.jpeg *.bmp *.gif);;Alle Dateien (*)"
        )
        if not path:
            return

        try:
            img = load_image(path)
            resized = resize_to_panel(img, self._rows(), self._cols())
            bitmap = image_to_bitmap(resized, self._rows())

            # Bitmap in Matrix konvertieren (via temporäres DrawingGrid)
            temp_grid = DrawingGrid(self._rows(), self._cols())
            temp_grid.from_bitmap(bitmap)
            matrix = temp_grid.get_matrix()

            self._frames.append(matrix)
            self._frame_list.addItem(f"Frame {len(self._frames)}")
            self._frame_list.setCurrentRow(len(self._frames) - 1)
            self._update_thumbnail(len(self._frames) - 1)
        except Exception as e:
            pass  # Fehler still ignorieren

    def _duplicate_frame(self) -> None:
        """Dupliziert den aktuellen Frame."""
        if self._current_frame < 0:
            return
        matrix = [row[:] for row in self._frames[self._current_frame]]
        self._frames.append(matrix)
        self._frame_list.addItem(f"Frame {len(self._frames)}")
        self._frame_list.setCurrentRow(len(self._frames) - 1)
        self._update_thumbnail(len(self._frames) - 1)

    def _remove_frame(self) -> None:
        """Entfernt den aktuellen Frame."""
        if len(self._frames) <= 1 or self._current_frame < 0:
            return  # Mindestens 1 Frame behalten
        idx = self._current_frame
        self._frames.pop(idx)
        self._frame_list.takeItem(idx)
        self._renumber_frames()

    def _move_frame_up(self) -> None:
        """Verschiebt den aktuellen Frame nach oben."""
        idx = self._current_frame
        if idx <= 0:
            return
        self._frames[idx], self._frames[idx - 1] = self._frames[idx - 1], self._frames[idx]
        self._renumber_frames()
        self._frame_list.setCurrentRow(idx - 1)
        self._update_thumbnail(idx)
        self._update_thumbnail(idx - 1)

    def _move_frame_down(self) -> None:
        """Verschiebt den aktuellen Frame nach unten."""
        idx = self._current_frame
        if idx < 0 or idx >= len(self._frames) - 1:
            return
        self._frames[idx], self._frames[idx + 1] = self._frames[idx + 1], self._frames[idx]
        self._renumber_frames()
        self._frame_list.setCurrentRow(idx + 1)
        self._update_thumbnail(idx)
        self._update_thumbnail(idx + 1)

    def _renumber_frames(self) -> None:
        """Nummeriert die Frame-Liste neu."""
        for i in range(self._frame_list.count()):
            self._frame_list.item(i).setText(f"Frame {i + 1}")

    def _update_thumbnail(self, index: int) -> None:
        """Aktualisiert das Thumbnail eines Frames in der Liste."""
        if index < 0 or index >= len(self._frames):
            return
        # Kleines Thumbnail-Bild erzeugen
        matrix = self._frames[index]
        rows = len(matrix)
        cols = len(matrix[0]) if matrix else 0
        if rows == 0 or cols == 0:
            return

        # QImage erstellen (skaliert auf ~120x40 für die Liste)
        img = QImage(cols, rows, QImage.Format.Format_RGB32)
        img.fill(QColor(10, 10, 10))
        for r in range(rows):
            for c in range(cols):
                if matrix[r][c]:
                    img.setPixelColor(c, r, QColor(0, 255, 50))

        pixmap = QPixmap.fromImage(img).scaled(
            120, 40, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        item = self._frame_list.item(index)
        if item:
            item.setIcon(pixmap)

    # --- Callbacks ---

    def _on_frame_selected(self, row: int) -> None:
        """Wird aufgerufen wenn ein Frame in der Liste ausgewählt wird."""
        # Aktuellen Frame-Stand speichern bevor gewechselt wird
        if 0 <= self._current_frame < len(self._frames):
            self._frames[self._current_frame] = self._grid.get_matrix()
            self._update_thumbnail(self._current_frame)

        self._current_frame = row
        if 0 <= row < len(self._frames):
            self._grid.set_matrix(self._frames[row])
            self._update_preview()

    def _on_grid_changed(self) -> None:
        """Grid wurde geändert → Frame speichern + Vorschau aktualisieren."""
        if 0 <= self._current_frame < len(self._frames):
            self._frames[self._current_frame] = self._grid.get_matrix()
            self._update_thumbnail(self._current_frame)
        self._update_preview()

    def _update_preview(self) -> None:
        """Aktualisiert die LED-Vorschau aus dem aktuellen Grid."""
        bitmap = self._grid.to_bitmap()
        self._preview.set_bitmap(bitmap, self._grid.rows)

    def _on_size_changed(self) -> None:
        """Panel-Größe geändert → alle Frames und Grid anpassen."""
        rows = self._rows()
        cols = self._cols()
        # Alle Frames auf neue Größe setzen (Daten gehen verloren)
        self._frames = [self._blank_matrix() for _ in range(len(self._frames))]
        self._grid.set_size(rows, cols)
        self._preview.set_size(rows, cols)
        for i in range(len(self._frames)):
            self._update_thumbnail(i)

    # --- Play/Stop ---

    def _on_play_toggled(self, checked: bool) -> None:
        """Startet oder stoppt die Animations-Vorschau."""
        if checked:
            self._playing = True
            self._play_btn.setText("Stop")
            self._play_timer.start(self._speed_slider.value())
        else:
            self._playing = False
            self._play_btn.setText("Vorschau abspielen")
            self._play_timer.stop()

    def _on_play_tick(self) -> None:
        """Timer-Tick: nächsten Frame anzeigen."""
        if not self._frames:
            return
        # Nächsten Frame in der Vorschau anzeigen (ohne Frame-Wechsel im Editor)
        next_idx = (self._current_frame + 1) % len(self._frames)
        self._frame_list.setCurrentRow(next_idx)
        # Timer-Intervall aktualisieren (falls Slider verändert wurde)
        self._play_timer.setInterval(self._speed_slider.value())

    # --- Senden ---

    def _on_send(self) -> None:
        """Sendet alle Frames als Animation."""
        # Aktuellen Frame-Stand speichern
        if 0 <= self._current_frame < len(self._frames):
            self._frames[self._current_frame] = self._grid.get_matrix()

        # Alle Frames in Bitmaps konvertieren
        bitmaps = []
        for matrix in self._frames:
            # Matrix → DrawingGrid → Bitmap
            temp = DrawingGrid(self._rows(), self._cols())
            temp.set_matrix(matrix)
            bitmaps.append(temp.to_bitmap())

        speed = self._speed_slider.value()
        self.send_animation_requested.emit(bitmaps, speed)

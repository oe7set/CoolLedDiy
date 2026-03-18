"""
QApplication + qasync Event-Loop Bootstrap.

Initialisiert die PySide6-Anwendung mit qasync für asyncio-Integration
(nötig für bleak BLE-Operationen in GUI-Callbacks).
"""

import asyncio
import logging
import sys

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from coolled.gui.main_window import MainWindow

logger = logging.getLogger(__name__)


def run() -> int:
    """Startet die CoolLedDiy Anwendung.

    Setzt QApplication + qasync QEventLoop auf und zeigt das Hauptfenster.

    Returns:
        Exit-Code der Anwendung
    """
    # Logging konfigurieren
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # QApplication erstellen
    app = QApplication(sys.argv)
    app.setApplicationName("CoolLedDiy")
    app.setOrganizationName("CoolLedDiy")

    # qasync Event-Loop einrichten (verbindet Qt Event-Loop mit asyncio)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Hauptfenster erstellen und anzeigen
    window = MainWindow()
    window.show()

    # Event-Loop starten
    with loop:
        logger.info("CoolLedDiy gestartet")
        return loop.run_forever()

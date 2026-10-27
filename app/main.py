"""Точка входа Genis."""

from __future__ import annotations

import ctypes
import logging
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import Qt
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from . import APP_NAME, COMPANY, __version__
from .config import load_config
from .paths import MODEL_MIN_BYTES, ensure_model, log_path, model_path
from .ui.icons import app_icon
from .ui.theme import apply_theme

SINGLE_INSTANCE_KEY = "Genis-single-instance-v1"


def _setup_logging() -> None:
    root = logging.getLogger()
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return
    root.setLevel(logging.INFO)
    # comtypes (через pygrabber) любит писать служебные INFO в общий лог.
    logging.getLogger("comtypes").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        file_handler = RotatingFileHandler(
            log_path(), maxBytes=1_000_000, backupCount=2, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        pass
    # В pythonw.exe sys.stderr может отсутствовать.
    if sys.stderr is not None:
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        root.addHandler(stream)


def _set_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


class _InstanceGuard:
    """Не даёт запустить вторую копию; по подключению показывает окно."""

    def __init__(self, on_show):
        self.server = QLocalServer()
        QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
        self.server.newConnection.connect(self._on_connection)
        self.server.listen(SINGLE_INSTANCE_KEY)
        self._on_show = on_show

    def _on_connection(self) -> None:
        socket = self.server.nextPendingConnection()
        if socket is not None:
            socket.readAll()
            socket.disconnectFromServer()
            socket.deleteLater()
        self._on_show()


def _ensure_model_ui() -> bool:
    path = model_path()
    if path.exists() and path.stat().st_size >= MODEL_MIN_BYTES:
        return True

    dialog = QProgressDialog(
        "Скачивается модель распознавания руки (несколько мегабайт)…", "", 0, 100
    )
    dialog.setWindowTitle(APP_NAME)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    dialog.setMinimumDuration(0)
    dialog.setAutoClose(False)
    dialog.setAutoReset(False)
    dialog.setCancelButton(None)
    dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    dialog.show()

    def progress(done: int, total: int) -> None:
        if total:
            dialog.setValue(int(done * 100 / total))
        QApplication.processEvents()

    try:
        ensure_model(progress)
    except Exception as exc:  # noqa: BLE001
        dialog.close()
        QMessageBox.critical(
            None,
            APP_NAME,
            "Не удалось скачать модель распознавания руки.\n\n"
            f"{exc}\n\nПроверь подключение к интернету и запусти Genis снова.",
        )
        return False
    dialog.close()
    return True


def main() -> int:
    _set_dpi_awareness()
    _setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(COMPANY)
    apply_theme(app)
    app.setWindowIcon(app_icon())
    app.setQuitOnLastWindowClosed(False)

    probe = QLocalSocket()
    probe.connectToServer(SINGLE_INSTANCE_KEY)
    if probe.waitForConnected(300):
        probe.write(b"show")
        probe.flush()
        probe.waitForBytesWritten(300)
        probe.disconnectFromServer()
        return 0

    if not _ensure_model_ui():
        return 1

    cfg = load_config()

    from .controller import AppController

    controller = AppController(app, cfg)
    guard = _InstanceGuard(controller.show_window)
    app._genis_guard = guard  # type: ignore[attr-defined]
    controller.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

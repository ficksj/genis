"""Контроллер приложения: связывает движок, камеру, окно и трей."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QSystemTrayIcon

from .config import default_config, get_gesture_meta, save_config
from .core.camera import CameraWorker
from .core.cameras import resolve_index
from .core.engine import EngineEvent, GestureEngine
from .core.hotkey import GlobalHotkey, pretty_combo
from .paths import data_dir

logger = logging.getLogger("genis")


class AppController(QObject):
    previewReady = Signal(QImage)
    reportReady = Signal(object)
    statusReady = Signal(dict)
    cameraFailed = Signal(str)
    logMessage = Signal(str)
    pausedChanged = Signal(bool)

    def __init__(self, app, cfg: dict[str, Any]):
        super().__init__()
        self.app = app
        self.cfg = cfg
        self.engine = GestureEngine(cfg, self._on_engine_event)
        self.window = None
        self.tray = None
        self.worker: CameraWorker | None = None
        self.quitting = False
        self.hotkey: GlobalHotkey | None = None
        self._camera_error = False

        self.previewReady.connect(self._on_preview)


    # --- запуск ----------------------------------------------------------
    def start(self) -> None:
        from .ui.main_window import MainWindow
        from .ui.tray import TrayIcon

        self.window = MainWindow(self)
        self.tray = TrayIcon(self)
        self.start_camera()
        self.reload_hotkey()

        if self.cfg.get("app", {}).get("show_window_on_start", True):
            self.show_window()
        self.log(
            "Genis запущен. Ctrl+Alt+Q — пауза, настройки — в трее."
            if not self.engine.paused
            else "Genis запущен в режиме паузы."
        )

        if self.cfg.get("app", {}).get("first_run", False):
            self.cfg["app"]["first_run"] = False
            self.save()
            self.log(
                "Первый запуск: открой «Камера», проверь распознавание и настрой жесты."
            )
            if self.tray is not None:
                self.tray.showMessage(
                    "Добро пожаловать в Genis",
                    "Покажи руку в камеру. Ctrl+Alt+Q — пауза. "
                    "Все настройки — в трее и в разделе «Жесты».",
                    QSystemTrayIcon.MessageIcon.Information,
                    6000,
                )

    # --- камера ----------------------------------------------------------
    def start_camera(self) -> None:
        self.stop_camera()
        self._camera_error = False
        camera = self.cfg.get("camera", {})
        # Камера могла переехать на другой индекс — ищем её по имени.
        camera["index"] = resolve_index(
            str(camera.get("device_name", "")), int(camera.get("index", 0))
        )
        worker = CameraWorker(self.cfg, self.engine)
        worker.preview.connect(self.previewReady)
        worker.report.connect(self.reportReady)
        worker.status.connect(self.statusReady)
        worker.log.connect(self.log)
        worker.failed.connect(self._on_camera_failed)
        worker.start()
        self.worker = worker

    def stop_camera(self) -> None:
        worker = self.worker
        self.worker = None
        if worker is None:
            return
        worker.request_stop()
        # Сначала отключаем сигналы, чтобы старый поток не слал кадры,
        # пока новый уже запускается.
        for signal in (worker.preview, worker.report, worker.status, worker.log, worker.failed):
            try:
                signal.disconnect()
            except (RuntimeError, TypeError):
                pass
        if not worker.wait(4000):
            logger.warning("Поток камеры не завершился за 4 секунды")
        worker.deleteLater()

    def restart_camera(self) -> None:
        self.log("Перезапуск камеры…")
        self.start_camera()

    def _on_camera_failed(self, message: str) -> None:
        self._camera_error = True
        self.log(f"⚠ {message}")
        self.cameraFailed.emit(message)
        if self.tray is not None:
            self.tray.set_error(True)

    def _on_preview(self, image: QImage) -> None:
        if self._camera_error:
            self._camera_error = False
            if self.tray is not None:
                self.tray.set_error(False)

    # --- пауза -----------------------------------------------------------
    def set_paused(self, paused: bool) -> None:
        paused = bool(paused)
        if paused == self.engine.paused:
            self.pausedChanged.emit(paused)
            return
        self.engine.set_paused(paused)
        self.pausedChanged.emit(paused)
        if self.tray is not None:
            self.tray.refresh()
        self.log("Пауза — жесты не выполняются" if paused else "Слежение продолжено")

    def toggle_pause(self) -> None:
        self.set_paused(not self.engine.paused)

    def set_suspended(self, suspended: bool) -> None:
        self.engine.set_suspended(suspended)

    # --- события движка --------------------------------------------------
    def _on_engine_event(self, event: EngineEvent) -> None:
        if event.kind == "action":
            name = get_gesture_meta(event.gesture, self.cfg).get("name", event.gesture)
            if event.error:
                self.log(f"⚠ «{name}»: {event.error}")
            else:
                self.log(f"«{name}» → {event.text}")
                self._beep()
        elif event.kind == "drag":
            name = get_gesture_meta(event.gesture, self.cfg).get("name", event.gesture)
            self.log(f"«{name}»: {event.text}")

    def _beep(self) -> None:
        if not self.cfg.get("engine", {}).get("sounds", False):
            return
        if sys.platform != "win32":
            return
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

    # --- жесты -----------------------------------------------------------
    def record_gesture(self) -> None:
        from PySide6.QtWidgets import QDialog

        from .ui.record_dialog import RecordGestureDialog

        self.show_window()
        dialog = RecordGestureDialog(self, self.window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.window is not None:
                self.window.refresh_all()
            self.show_window()

    # --- настройки -------------------------------------------------------
    def save(self) -> None:
        try:
            save_config(self.cfg)
        except OSError as exc:
            self.log(f"⚠ Не удалось сохранить настройки: {exc}")

    def reset_config(self) -> None:
        fresh = default_config()
        self.cfg.clear()
        self.cfg.update(fresh)
        self.save()
        self.engine.reload()
        self.restart_camera()
        self.reload_hotkey()
        self.set_paused(bool(self.cfg["app"].get("start_paused", False)))
        if self.window is not None:
            self.window.refresh_all()
        if self.tray is not None:
            self.tray.refresh()
        self.log("Настройки сброшены к значениям по умолчанию")

    def set_autostart(self, enabled: bool) -> None:
        ok = self.engine.system.set_autostart(enabled)
        if not ok:
            self.log("⚠ Не удалось изменить автозапуск")
        else:
            self.log("Автозапуск включён" if enabled else "Автозапуск выключен")

    def open_data_folder(self) -> None:
        try:
            os.startfile(data_dir())  # noqa: S606
        except OSError as exc:
            self.log(f"⚠ Не удалось открыть папку: {exc}")

    def reload_hotkey(self) -> None:
        if self.hotkey is None:
            self.hotkey = GlobalHotkey(self)
            self.hotkey.triggered.connect(self.toggle_pause)
        else:
            self.hotkey.unregister()

        combo = str(self.cfg.get("engine", {}).get("pause_hotkey", "")).strip()
        if not combo:
            self.log("Горячая клавиша паузы отключена")
            return
        ok, error = self.hotkey.register(combo)
        if ok:
            logger.info("Горячая клавиша %s зарегистрирована через %s", combo, self.hotkey.backend)
        else:
            self.log(f"⚠ Не удалось включить горячую клавишу {pretty_combo(combo)}: {error}")

    # --- окно ------------------------------------------------------------
    def show_window(self) -> None:
        if self.window is None:
            return
        if self.window.isMinimized():
            self.window.showNormal()
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def hide_window(self) -> None:
        if self.window is not None:
            self.window.hide()

    def show_page(self, key: str) -> None:
        if self.window is None:
            return
        self.show_window()
        self.window.show_page(key)

    def log(self, text: str) -> None:
        line = f"{datetime.now():%H:%M:%S}  {text}"
        logger.info(text)
        self.logMessage.emit(line)

    def quit_app(self) -> None:
        if self.quitting:
            return
        self.quitting = True
        self.stop_camera()
        if self.hotkey is not None:
            self.hotkey.unregister()
        self.save()
        if self.tray is not None:
            self.tray.hide()
        self.app.quit()

"""Значок и меню в системном трее."""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .. import __version__
from .icons import tray_icon


class TrayIcon(QSystemTrayIcon):
    def __init__(self, controller):
        super().__init__(tray_icon(True, controller.engine.paused))
        self.controller = controller
        self._error = False
        self._hidden_notice = False

        self.setToolTip("Genis — управление жестами · Crazy Monkeys")
        self._build_menu()
        self.activated.connect(self._on_activated)

        controller.pausedChanged.connect(lambda _value: self.refresh())
        self.refresh()
        self.show()

    def _build_menu(self) -> None:
        menu = QMenu()

        header = QAction(f"Genis {__version__} · Crazy Monkeys", menu)
        header.setEnabled(False)
        menu.addAction(header)
        menu.addSeparator()

        show_action = QAction("Открыть Genis", menu)
        show_action.triggered.connect(self.controller.show_window)
        menu.addAction(show_action)

        self.pause_action = QAction("Слежение включено", menu)
        self.pause_action.setCheckable(True)
        self.pause_action.setChecked(not self.controller.engine.paused)
        self.pause_action.toggled.connect(lambda checked: self.controller.set_paused(not checked))
        menu.addAction(self.pause_action)
        menu.addSeparator()

        record_action = QAction("Записать свой жест…", menu)
        record_action.triggered.connect(self.controller.record_gesture)
        menu.addAction(record_action)

        settings_action = QAction("Настройки…", menu)
        settings_action.triggered.connect(lambda: self.controller.show_page("settings"))
        menu.addAction(settings_action)

        folder_action = QAction("Открыть папку настроек", menu)
        folder_action.triggered.connect(self.controller.open_data_folder)
        menu.addAction(folder_action)
        menu.addSeparator()

        quit_action = QAction("Выход", menu)
        quit_action.triggered.connect(self.controller.quit_app)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self._menu = menu

    def refresh(self) -> None:
        paused = self.controller.engine.paused
        self.setIcon(tray_icon(not paused, paused, self._error))
        if self._error:
            status = "камера недоступна"
        elif paused:
            status = "пауза"
        else:
            status = "слежение активно"
        self.setToolTip(f"Genis — {status}")
        self.pause_action.blockSignals(True)
        self.pause_action.setChecked(not paused)
        self.pause_action.blockSignals(False)

    def set_error(self, error: bool) -> None:
        self._error = bool(error)
        self.refresh()

    def notify_hidden(self) -> None:
        if self._hidden_notice:
            return
        self._hidden_notice = True
        self.showMessage(
            "Genis работает в трее",
            "Двойной клик по значку — открыть настройки. "
            "Ctrl+Alt+Q — пауза.",
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )

    def _on_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.controller.show_window()

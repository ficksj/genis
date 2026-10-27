"""Главное окно: боковая навигация, страницы, брендинг."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from .icons import app_icon
from .pages import CameraPage, DashboardPage, GesturesPage, SettingsPage
from .widgets import BrandBlock, Divider


class MainWindow(QMainWindow):
    PAGES = (
        ("overview", "Обзор", DashboardPage),
        ("gestures", "Жесты", GesturesPage),
        ("camera", "Камера", CameraPage),
        ("settings", "Настройки", SettingsPage),
    )

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.cfg = controller.cfg
        self._buttons: list[QPushButton] = []

        self.setWindowTitle("Genis — управление жестами")
        self.setWindowIcon(app_icon())
        self.resize(1180, 800)
        self.setMinimumSize(1100, 720)

        central = QWidget()
        central.setObjectName("Central")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        self.pages: dict[str, QWidget] = {}
        for key, _label, page_class in self.PAGES:
            page = page_class(controller)
            self.pages[key] = page
            self.stack.addWidget(page)
        root.addWidget(self.stack, 1)

        self.setCentralWidget(central)
        self.show_page("overview")

    # --- сайдбар ---------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("SidebarFrame")
        sidebar.setFixedWidth(236)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 18)
        layout.setSpacing(16)

        layout.addWidget(BrandBlock())
        layout.addWidget(Divider())

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        nav = QVBoxLayout()
        nav.setSpacing(4)
        for index, (_key, label, _cls) in enumerate(self.PAGES):
            button = QPushButton(label)
            button.setObjectName("Nav")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, i=index: self._select(i))
            self._group.addButton(button, index)
            self._buttons.append(button)
            nav.addWidget(button)
        layout.addLayout(nav)
        layout.addStretch(1)

        layout.addWidget(Divider())

        hint = QLabel("ПАУЗА  ·  CTRL + ALT + Q")
        hint.setObjectName("Mono")
        hint.setStyleSheet("font-size: 9px; letter-spacing: 0.6px;")
        layout.addWidget(hint)

        made = QLabel("Сделано командой")
        made.setObjectName("Footer")
        layout.addWidget(made)

        team = QLabel("CRAZY MONKEYS")
        team.setObjectName("FooterStrong")
        team.setStyleSheet("letter-spacing: 0.8px;")
        layout.addWidget(team)

        version = QLabel(f"Genis {__version__}")
        version.setObjectName("Footer")
        version.setStyleSheet("font-size: 9px;")
        layout.addWidget(version)
        return sidebar

    # --- навигация -------------------------------------------------------
    def _select(self, index: int) -> None:
        if index < 0 or index >= len(self.PAGES):
            return
        self.stack.setCurrentIndex(index)
        self._buttons[index].setChecked(True)

    def show_page(self, key: str) -> None:
        for index, (page_key, _label, _cls) in enumerate(self.PAGES):
            if page_key == key:
                self._select(index)
                break
        self.show()
        self.raise_()
        self.activateWindow()

    def refresh_all(self) -> None:
        for page in self.pages.values():
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                refresh()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.controller.quitting:
            event.accept()
            return
        if self.cfg.get("app", {}).get("minimize_to_tray", True):
            event.ignore()
            self.hide()
            if self.controller.tray is not None:
                self.controller.tray.notify_hidden()
        else:
            event.ignore()
            self.controller.quit_app()

"""Диалог настройки действия, привязанного к жесту."""

from __future__ import annotations

import copy
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.actions import (
    ACTION_TYPES,
    BRIGHTNESS_MODES,
    MOUSE_ACTIONS,
    default_action,
)
from ..core.system_win import MEDIA_LABELS, WINDOW_LABELS
from .widgets import HotkeyEdit


class ActionDialog(QDialog):
    def __init__(
        self,
        action: dict[str, Any] | None,
        cfg: dict[str, Any] | None = None,
        parent=None,
        title: str = "Действие жеста",
    ):
        super().__init__(parent)
        self.cfg = cfg or {}
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self._widgets: dict[str, dict[str, Any]] = {}

        self._source = copy.deepcopy(action) if action else default_action("none")
        self._build_ui()
        self._load(self._source)

    # --- построение ------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(14)

        title = QLabel("Что сделать при этом жесте?")
        title.setObjectName("DialogTitle")
        root.addWidget(title)

        self.type_combo = QComboBox()
        for key, label in ACTION_TYPES:
            self.type_combo.addItem(label, key)
        root.addWidget(self.type_combo)

        self.stack = QStackedWidget()
        self.stack.setMinimumHeight(0)
        for key, _label in ACTION_TYPES:
            page = self._make_page(key)
            self.stack.addWidget(page)
        root.addWidget(self.stack, 1)

        self.hint = QLabel("")
        self.hint.setObjectName("Muted")
        self.hint.setWordWrap(True)
        root.addWidget(self.hint)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Отмена")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Сохранить")
        save.setObjectName("Primary")
        save.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)

        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self._on_type_changed()

    def _make_page(self, kind: str) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(0, 4, 0, 0)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        if kind in ("none", "cursor_move", "scroll"):
            text = {
                "none": "Жест будет распознаваться, но ничего не делать. Удобно для паузы.",
                "cursor_move": "Курсор будет следовать за кончиком указательного пальца.\n"
                "Работает только с жестами, где виден указательный палец.",
                "scroll": "Движение руки вверх/вниз будет прокручивать страницу.\n"
                "Скорость настраивается в «Настройках».",
            }[kind]
            label = QLabel(text)
            label.setWordWrap(True)
            label.setObjectName("Muted")
            form.addRow(label)

        elif kind == "mouse":
            button = QComboBox()
            for key, label in (("left", "Левая"), ("right", "Правая"), ("middle", "Средняя")):
                button.addItem(label, key)
            action = QComboBox()
            for key, label in MOUSE_ACTIONS:
                action.addItem(label, key)
            drag = QCheckBox("Удержание жеста = перетаскивание")
            drag.setToolTip("Для щипка: короткий щипок — клик, длинный — перетаскивание объекта")
            form.addRow("Кнопка", button)
            form.addRow("Что сделать", action)
            form.addRow("", drag)
            self._widgets[kind] = {"button": button, "action": action, "drag": drag}

        elif kind == "hotkey":
            keys = HotkeyEdit()
            form.addRow("Комбинация", keys)
            note = QLabel("Кликните в поле и нажмите нужные клавиши")
            note.setObjectName("Muted")
            form.addRow("", note)
            self._widgets[kind] = {"keys": keys}

        elif kind == "launch":
            target = QLineEdit()
            target.setPlaceholderText(r"C:\Program Files\...\app.exe, notepad.exe, https://…, steam://…")

            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            browse = QPushButton("Файл…")
            browse.setObjectName("Ghost")
            browse.clicked.connect(lambda: self._pick_file(target))

            library = QComboBox()
            library.addItem("Из библиотеки…", "")
            library.setMinimumWidth(150)
            for item in self.cfg.get("library", []):
                library.addItem(item.get("name", "?"), item.get("target", ""))
            library.currentIndexChanged.connect(
                lambda idx: self._use_library(library, target, idx)
            )

            row_layout.addWidget(target, 1)
            row_layout.addWidget(browse)
            row_layout.addWidget(library)
            form.addRow("Программа или ссылка", row)
            note = QLabel("Поддерживаются .exe, .lnk, файлы, папки, http(s):// и steam://")
            note.setObjectName("Muted")
            form.addRow("", note)
            self._widgets[kind] = {"target": target}

        elif kind == "media":
            key = QComboBox()
            for value, label in MEDIA_LABELS.items():
                key.addItem(label, value)
            form.addRow("Команда", key)
            self._widgets[kind] = {"key": key}

        elif kind == "brightness":
            mode = QComboBox()
            for value, label in BRIGHTNESS_MODES:
                mode.addItem(label, value)
            step = QSpinBox()
            step.setRange(1, 50)
            step.setSuffix(" %")
            value = QSpinBox()
            value.setRange(0, 100)
            value.setSuffix(" %")
            form.addRow("Режим", mode)
            form.addRow("Шаг", step)
            form.addRow("Значение", value)
            mode.currentIndexChanged.connect(
                lambda: self._update_brightness_widgets(mode, step, value)
            )
            self._widgets[kind] = {"mode": mode, "step": step, "value": value}

        elif kind == "window":
            command = QComboBox()
            for value, label in WINDOW_LABELS.items():
                command.addItem(label, value)
            form.addRow("Команда", command)
            self._widgets[kind] = {"command": command}

        elif kind == "text":
            text = QPlainTextEdit()
            text.setPlaceholderText("Текст, который будет напечатан")
            text.setFixedHeight(90)
            form.addRow("Текст", text)
            self._widgets[kind] = {"text": text}

        elif kind == "command":
            command = QLineEdit()
            command.setPlaceholderText("например: explorer.exe C:\\Users")
            form.addRow("Команда", command)
            note = QLabel("Выполняется через cmd.exe. Используй только свои команды.")
            note.setObjectName("Muted")
            form.addRow("", note)
            self._widgets[kind] = {"command": command}

        return page

    @staticmethod
    def _pick_file(target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Выберите программу",
            "",
            "Программы (*.exe *.bat *.cmd *.lnk);;Все файлы (*.*)",
        )
        if path:
            target.setText(path)

    def _use_library(self, combo: QComboBox, target: QLineEdit, index: int) -> None:
        value = combo.itemData(index)
        if value:
            target.setText(str(value))
        combo.blockSignals(True)
        combo.setCurrentIndex(0)
        combo.blockSignals(False)

    @staticmethod
    def _update_brightness_widgets(mode: QComboBox, step: QSpinBox, value: QSpinBox) -> None:
        is_set = mode.currentData() == "set"
        step.setEnabled(not is_set)
        value.setEnabled(is_set)

    def _on_type_changed(self) -> None:
        kind = self.type_combo.currentData()
        current = 0
        for i in range(self.stack.count()):
            if ACTION_TYPES[i][0] == kind:
                current = i
                break
        self.stack.setCurrentIndex(current)

        # Скрытые страницы не должны растягивать диалог: подгоняем высоту
        # под текущую форму.
        for i in range(self.stack.count()):
            page = self.stack.widget(i)
            policy = page.sizePolicy()
            policy.setVerticalPolicy(
                QSizePolicy.Policy.Preferred
                if i == current
                else QSizePolicy.Policy.Ignored
            )
            page.setSizePolicy(policy)
        self.adjustSize()

        hints = {
            "none": "Жест будет молчать.",
            "cursor_move": "Курсор двигается, пока жест удерживается.",
            "scroll": "Прокрутка, пока жест удерживается.",
            "mouse": "Для щипка можно включить перетаскивание.",
            "hotkey": "Например: ctrl+shift+esc, alt+f4, win+d.",
            "launch": "Можно запускать программы, сайты и ссылки вида steam://.",
            "media": "Работает с любым активным плеером.",
            "brightness": "Только для экранов ноутбуков (WMI).",
            "window": "Стандартные сочетания Windows.",
            "text": "Текст печатается в активное окно.",
            "command": "Для продвинутых: обычная команда cmd.exe.",
        }
        self.hint.setText(hints.get(kind, ""))

    # --- загрузка/сохранение --------------------------------------------
    def _load(self, action: dict[str, Any]) -> None:
        kind = action.get("type", "none")
        index = self.type_combo.findData(kind)
        self.type_combo.setCurrentIndex(max(0, index))
        self._on_type_changed()
        params = action.get("params") or {}
        w = self._widgets.get(kind, {})

        if kind == "mouse":
            self._select(w["button"], params.get("button", "left"))
            self._select(w["action"], params.get("action", "click"))
            w["drag"].setChecked(bool(params.get("drag", False)))
        elif kind == "hotkey":
            w["keys"].set_combo(params.get("keys", ""))
        elif kind == "launch":
            w["target"].setText(str(params.get("target", "")))
        elif kind == "media":
            self._select(w["key"], params.get("key", "play_pause"))
        elif kind == "brightness":
            self._select(w["mode"], params.get("mode", "up"))
            w["step"].setValue(int(params.get("step", 10)))
            w["value"].setValue(int(params.get("value", 50)))
            self._update_brightness_widgets(w["mode"], w["step"], w["value"])
        elif kind == "window":
            self._select(w["command"], params.get("command", "show_desktop"))
        elif kind == "text":
            w["text"].setPlainText(str(params.get("text", "")))
        elif kind == "command":
            w["command"].setText(str(params.get("command", "")))

    @staticmethod
    def _select(combo: QComboBox, value: Any) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def action(self) -> dict[str, Any]:
        kind = self.type_combo.currentData()
        params: dict[str, Any] = {}
        w = self._widgets.get(kind, {})

        if kind == "mouse":
            params = {
                "button": w["button"].currentData(),
                "action": w["action"].currentData(),
                "drag": w["drag"].isChecked(),
            }
        elif kind == "hotkey":
            params = {"keys": w["keys"].combo()}
        elif kind == "launch":
            params = {"target": w["target"].text().strip()}
        elif kind == "media":
            params = {"key": w["key"].currentData()}
        elif kind == "brightness":
            params = {
                "mode": w["mode"].currentData(),
                "step": w["step"].value(),
                "value": w["value"].value(),
            }
        elif kind == "window":
            params = {"command": w["command"].currentData()}
        elif kind == "text":
            params = {"text": w["text"].toPlainText()}
        elif kind == "command":
            params = {"command": w["command"].text().strip()}

        return {"type": kind, "params": params}

"""Страницы главного окна: обзор, жесты, камера, настройки."""

from __future__ import annotations

import os
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..config import BUILTIN_GESTURES, get_gesture_meta
from ..core.actions import describe
from ..core.builtin import describe_fingers
from ..core.cameras import list_cameras
from ..paths import data_dir
from .action_dialog import ActionDialog
from .logo import badge_pixmap
from .theme import ACCENT
from .widgets import (
    Card,
    Chip,
    Divider,
    HeroCard,
    HotkeyEdit,
    PreviewLabel,
    StatBlock,
    StatusPill,
)


def section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("H2")
    return label


def kicker(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("SectionKicker")
    return label


def muted(text: str = "", wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Muted")
    label.setWordWrap(wrap)
    return label


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def page_header(title: str, subtitle: str = "", right: QWidget | None = None) -> QVBoxLayout:
    column = QVBoxLayout()
    column.setSpacing(4)
    row = QHBoxLayout()
    row.setSpacing(12)
    label = QLabel(title)
    label.setObjectName("H1")
    row.addWidget(label)
    row.addStretch(1)
    if right is not None:
        row.addWidget(right)
    column.addLayout(row)
    if subtitle:
        column.addWidget(muted(subtitle, wrap=True))
    return column


def form_card(title: str, subtitle: str = "") -> tuple[Card, QFormLayout]:
    card = Card()
    outer = QVBoxLayout(card)
    outer.setContentsMargins(20, 18, 20, 18)
    outer.setSpacing(12)
    if title:
        outer.addWidget(section_title(title))
    if subtitle:
        outer.addWidget(muted(subtitle, wrap=True))
    form = QFormLayout()
    form.setSpacing(12)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    outer.addLayout(form)
    return card, form


class DashboardPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.cfg = controller.cfg
        self._camera_error = False
        self._build()

        controller.previewReady.connect(self._on_preview)
        controller.reportReady.connect(self._on_report)
        controller.statusReady.connect(self._on_status)
        controller.pausedChanged.connect(self._on_paused)
        controller.cameraFailed.connect(self._on_camera_failed)
        controller.logMessage.connect(self.append_log)
        self._on_paused(controller.engine.paused)

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        self.pill = StatusPill("Слежение активно", "on")
        root.addLayout(page_header("Обзор", right=self.pill))

        hero = HeroCard()
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        hero_layout.setSpacing(20)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)
        text_col.addWidget(kicker("Сейчас распознаётся"))
        self.gesture_label = QLabel("Нет руки в кадре")
        self.gesture_label.setObjectName("HeroGesture")
        self.gesture_label.setProperty("state", "idle")
        text_col.addWidget(self.gesture_label)
        self.action_label = QLabel("Покажи руку в камеру — управление начнётся сразу")
        self.action_label.setObjectName("HeroAction")
        self.action_label.setWordWrap(True)
        text_col.addWidget(self.action_label)
        hero_layout.addLayout(text_col, 1)

        buttons = QVBoxLayout()
        buttons.setSpacing(9)
        self.pause_button = QPushButton("Пауза")
        self.pause_button.setObjectName("Primary")
        self.pause_button.setMinimumWidth(190)
        self.pause_button.clicked.connect(self.controller.toggle_pause)
        self.record_button = QPushButton("Записать свой жест")
        self.record_button.setObjectName("Ghost")
        self.record_button.clicked.connect(self.controller.record_gesture)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.record_button)
        buttons.addStretch(1)
        hero_layout.addLayout(buttons)
        root.addWidget(hero)

        stats = Card()
        stats_layout = QHBoxLayout(stats)
        stats_layout.setContentsMargins(24, 16, 24, 16)
        stats_layout.setSpacing(0)
        self.stat_fps = StatBlock("FPS")
        self.stat_hands = StatBlock("Руки")
        self.stat_conf = StatBlock("Уверенность")
        self.stat_source = StatBlock("Источник")
        blocks = (self.stat_fps, self.stat_hands, self.stat_conf, self.stat_source)
        for index, block in enumerate(blocks):
            if index:
                line = Divider()
                line.setFixedWidth(1)
                line.setFixedHeight(34)
                stats_layout.addSpacing(22)
                stats_layout.addWidget(line)
                stats_layout.addSpacing(22)
            stats_layout.addWidget(block)
        stats_layout.addStretch(1)
        root.addWidget(stats)

        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        preview_card = Card()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(18, 16, 18, 18)
        preview_layout.setSpacing(10)
        preview_header = QHBoxLayout()
        preview_header.addWidget(section_title("Камера"))
        preview_header.addStretch(1)
        preview_header.addWidget(muted("живое превью"))
        preview_layout.addLayout(preview_header)
        self.preview = PreviewLabel()
        self.preview.setMinimumHeight(250)
        preview_layout.addWidget(self.preview, 1)
        bottom.addWidget(preview_card, 3)

        log_card = Card()
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(18, 16, 18, 16)
        log_layout.setSpacing(10)

        log_header = QHBoxLayout()
        log_header.addWidget(section_title("Журнал"))
        log_header.addStretch(1)
        clear_button = QPushButton("Очистить")
        clear_button.setObjectName("Link")
        clear_button.clicked.connect(lambda: self.log.clear())
        log_header.addWidget(clear_button)
        log_layout.addLayout(log_header)

        self.log = QPlainTextEdit()
        self.log.setObjectName("Log")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(400)
        self.log.setPlaceholderText("Здесь появятся распознанные жесты и действия…")
        log_layout.addWidget(self.log, 1)
        bottom.addWidget(log_card, 2)

        root.addLayout(bottom, 1)

    # --- обновления ------------------------------------------------------
    def _on_preview(self, image) -> None:
        self.preview.set_image(image)
        if self._camera_error:
            self._camera_error = False
            self._update_pill()

    def _on_report(self, report) -> None:
        state = report.state
        self.stat_fps.set_value(f"{report.fps:.0f}" if report.fps else "—")
        hands = len(getattr(report, "hands", []) or [])
        self.stat_hands.set_value(str(hands) if hands else "—")
        self.stat_conf.set_value(f"{state.confidence * 100:.0f}%" if state.hand else "—")
        self.stat_source.set_value(
            "свой" if state.source == "custom" else ("встроенный" if state.source else "—")
        )

        if state.gesture:
            meta = get_gesture_meta(state.gesture, self.cfg)
            self._set_hero(meta["name"], state.action or describe(self._action_for(state.gesture)))
        else:
            self._set_hero(
                "Нет руки в кадре",
                "Покажи руку в камеру — управление начнётся сразу",
                idle=True,
            )

    def _set_hero(self, title: str, action: str, idle: bool = False) -> None:
        self.gesture_label.setText(title)
        self.action_label.setText(action)
        state = "idle" if idle else "live"
        if self.gesture_label.property("state") != state:
            self.gesture_label.setProperty("state", state)
            self.gesture_label.style().unpolish(self.gesture_label)
            self.gesture_label.style().polish(self.gesture_label)

    def _action_for(self, gesture_id: str) -> dict[str, Any]:
        for custom in self.cfg.get("custom_gestures", []):
            if custom.get("id") == gesture_id:
                return custom.get("action") or {"type": "none", "params": {}}
        binding = self.cfg.get("bindings", {}).get(gesture_id) or {}
        return binding.get("action") or {"type": "none", "params": {}}

    def _on_status(self, data: dict) -> None:
        if data.get("fps"):
            self.stat_fps.set_value(f"{data['fps']:.0f}")
        if "hands" in data:
            count = int(data.get("hands") or 0)
            self.stat_hands.set_value(str(count) if count else "—")
        elif "hand" in data:
            self.stat_hands.set_value("1" if data.get("hand") else "—")
        self._update_pill()

    def _on_paused(self, paused: bool) -> None:
        self.pause_button.setText("Продолжить" if paused else "Пауза")
        self._update_pill()

    def _on_camera_failed(self, message: str) -> None:
        self._camera_error = True
        self._update_pill()
        self.append_log(f"⚠ {message}")

    def _update_pill(self) -> None:
        if self._camera_error:
            self.pill.set_state("off", "Камера недоступна")
        elif self.controller.engine.paused:
            self.pill.set_state("pause", "Пауза")
        else:
            self.pill.set_state("on", "Слежение активно")

    def append_log(self, line: str) -> None:
        self.log.appendPlainText(line)
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def refresh(self) -> None:
        self._update_pill()


class GesturesPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.cfg = controller.cfg

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        record = QPushButton("＋  Записать свой жест")
        record.setObjectName("Primary")
        record.clicked.connect(controller.record_gesture)
        root.addLayout(
            page_header(
                "Жесты",
                "Нажми на действие справа, чтобы выбрать, что делать при жесте. "
                "Свои жесты имеют приоритет, если совпадение уверенное.",
                right=record,
            )
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.rows = QVBoxLayout(container)
        self.rows.setContentsMargins(0, 4, 10, 8)
        self.rows.setSpacing(8)
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        self.refresh()

    def refresh(self) -> None:
        clear_layout(self.rows)

        self.rows.addWidget(kicker("Одна рука"))
        self.rows.addSpacing(2)
        for meta in (item for item in BUILTIN_GESTURES if not item.get("pair")):
            binding = self.cfg.get("bindings", {}).setdefault(meta["id"], {})
            binding.setdefault("enabled", True)
            binding.setdefault("action", {"type": "none", "params": {}})
            self.rows.addWidget(self._make_row(meta, binding, custom=False))

        self.rows.addSpacing(18)
        self.rows.addWidget(kicker("Две руки"))
        self.rows.addSpacing(2)
        self.rows.addWidget(
            muted(
                "Покажи обе руки одновременно — жест сработает, когда обе позы "
                "совпадут. Пока двурукий жест держится, одиночные действия не мешают.",
                wrap=True,
            )
        )
        for meta in (item for item in BUILTIN_GESTURES if item.get("pair")):
            binding = self.cfg.get("bindings", {}).setdefault(meta["id"], {})
            binding.setdefault("enabled", True)
            binding.setdefault("action", {"type": "none", "params": {}})
            self.rows.addWidget(self._make_row(meta, binding, custom=False))

        self.rows.addSpacing(18)
        self.rows.addWidget(kicker("Свои жесты"))
        self.rows.addSpacing(2)
        customs = self.cfg.get("custom_gestures", [])
        if not customs:
            empty = Card()
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(20, 18, 20, 18)
            empty_layout.setSpacing(4)
            empty_layout.addWidget(muted("Пока пусто."))
            empty_layout.addWidget(
                muted(
                    "Запиши свой жест — например, «открыть Steam» или «свернуть всё»."
                )
            )
            self.rows.addWidget(empty)
        for gesture in customs:
            hands_count = int(gesture.get("hands", 1))
            meta = {
                "id": gesture["id"],
                "name": gesture.get("name", "Свой жест"),
                "hint": (
                    f"{'две руки' if hands_count == 2 else 'одна рука'} · "
                    f"порог {float(gesture.get('threshold', 0.3)):.2f} · "
                    f"{int(gesture.get('samples', 0))} кадров при записи"
                ),
                "kind": "discrete",
                "custom": True,
                "hands": hands_count,
            }
            self.rows.addWidget(self._make_row(meta, gesture, custom=True))
        self.rows.addStretch(1)

    def _make_row(self, meta: dict, obj: dict, custom: bool) -> QWidget:
        card = Card()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 13, 16, 13)
        layout.setSpacing(14)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name = QLabel(meta["name"])
        name.setObjectName("H2")
        name_row.addWidget(name)
        if custom:
            tag = Chip("СВОЙ · 2 РУКИ" if int(meta.get("hands", 1)) == 2 else "СВОЙ")
            name_row.addWidget(tag)
        name_row.addStretch(1)
        text_col.addLayout(name_row)
        hint = QLabel(meta.get("hint", ""))
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        text_col.addWidget(hint)
        layout.addLayout(text_col, 1)

        action = obj.get("action") or {"type": "none", "params": {}}
        action_button = QPushButton(describe(action))
        action_button.setObjectName("Ghost")
        action_button.setMinimumWidth(240)
        action_button.setMaximumWidth(360)
        action_button.setToolTip(describe(action))
        action_button.clicked.connect(
            lambda: self._edit_action(meta, obj, action_button, custom)
        )
        layout.addWidget(action_button)

        enabled = QCheckBox()
        enabled.setChecked(bool(obj.get("enabled", True)))
        enabled.setToolTip("Включить жест")
        enabled.toggled.connect(lambda value: self._toggle(obj, value))
        layout.addWidget(enabled)

        if custom:
            delete = QPushButton("✕")
            delete.setObjectName("Danger")
            delete.setFixedWidth(38)
            delete.setToolTip("Удалить жест")
            delete.clicked.connect(lambda: self._delete(meta, obj))
            layout.addWidget(delete)

        return card

    def _edit_action(
        self, meta: dict, obj: dict, button: QPushButton, custom: bool
    ) -> None:
        dialog = ActionDialog(
            obj.get("action"), self.cfg, self, f"Жест «{meta['name']}»"
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            obj["action"] = dialog.action()
            self.controller.save()
            text = describe(obj["action"])
            button.setText(text)
            button.setToolTip(text)
            self.controller.log(f"«{meta['name']}» → {text}")

    def _toggle(self, obj: dict, value: bool) -> None:
        obj["enabled"] = bool(value)
        self.controller.save()

    def _delete(self, meta: dict, obj: dict) -> None:
        answer = QMessageBox.question(
            self,
            "Удалить жест",
            f"Удалить «{meta['name']}»? Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        customs = self.cfg.get("custom_gestures", [])
        if obj in customs:
            customs.remove(obj)
        self.controller.save()
        self.controller.log(f"Удалён жест «{meta['name']}»")
        self.refresh()


class CameraPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.cfg = controller.cfg

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        root.addLayout(
            page_header(
                "Камера",
                "Выбери камеру из списка и проверь распознавание. Свет должен падать "
                "на ладонь, а рука — быть целиком в кадре.",
            )
        )

        body = QHBoxLayout()
        body.setSpacing(16)

        preview_card = Card()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        preview_layout.setSpacing(12)
        self.preview = PreviewLabel("Камера выключена")
        preview_layout.addWidget(self.preview, 1)

        live = QHBoxLayout()
        live.setSpacing(8)
        self.chip_fps = Chip("FPS —")
        self.chip_res = Chip("— × —")
        self.chip_hands = Chip("РУКИ —")
        self.chip_gesture = Chip("ЖЕСТ —")
        self.chip_fingers = Chip("ПАЛЬЦЫ —")
        for chip in (
            self.chip_fps,
            self.chip_res,
            self.chip_hands,
            self.chip_gesture,
            self.chip_fingers,
        ):
            live.addWidget(chip)
        live.addStretch(1)
        preview_layout.addLayout(live)
        body.addWidget(preview_card, 3)

        controls = Card()
        controls.setMinimumWidth(300)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(20, 18, 20, 18)
        controls_layout.setSpacing(9)
        controls_layout.addWidget(kicker("Устройство"))
        controls_layout.addWidget(section_title("Источник видео"))

        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(120)
        self.camera_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.camera_combo.setMinimumContentsLength(14)
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setObjectName("Ghost")
        self.refresh_button.setToolTip("Перечитать список камер из DirectShow")
        self.refresh_button.clicked.connect(self.reload_cameras)
        camera_row = QHBoxLayout()
        camera_row.setSpacing(8)
        camera_row.addWidget(self.camera_combo, 1)
        camera_row.addWidget(self.refresh_button)

        controls_layout.addWidget(muted("Камера"))
        controls_layout.addLayout(camera_row)

        self.resolution = QComboBox()
        self.resolution.setMaximumWidth(200)
        for width, height in ((640, 480), (1280, 720), (1920, 1080)):
            self.resolution.addItem(f"{width} × {height}", (width, height))
        current = (
            int(self.cfg["camera"].get("width", 640)),
            int(self.cfg["camera"].get("height", 480)),
        )
        index = self.resolution.findData(current)
        if index >= 0:
            self.resolution.setCurrentIndex(index)
        controls_layout.addWidget(muted("Разрешение"))
        controls_layout.addWidget(self.resolution)

        self.max_hands = QComboBox()
        self.max_hands.setMaximumWidth(200)
        self.max_hands.addItem("1 — одна рука", 1)
        self.max_hands.addItem("2 — две руки", 2)
        current_hands = int(self.cfg.get("tracking", {}).get("max_hands", 2))
        hand_index = self.max_hands.findData(current_hands)
        if hand_index >= 0:
            self.max_hands.setCurrentIndex(hand_index)
        self.max_hands.setToolTip(
            "«2» включает жесты двумя руками: чуть больше нагрузка на процессор"
        )
        controls_layout.addWidget(muted("Сколько рук отслеживать"))
        controls_layout.addWidget(self.max_hands)

        self.mirror = QCheckBox("Зеркалить картинку")
        self.mirror.setToolTip("Отражает превью по горизонтали, как в зеркале")
        self.mirror.setChecked(bool(self.cfg["camera"].get("mirror", True)))
        controls_layout.addWidget(self.mirror)

        self.landmarks = QCheckBox("Скелет руки")
        self.landmarks.setToolTip("Рисовать 21 точку и линии пальцев поверх видео")
        self.landmarks.setChecked(bool(self.cfg["camera"].get("show_landmarks", True)))
        controls_layout.addWidget(self.landmarks)

        hint = muted(
            "Список читается из DirectShow. Если камеру подключили только что — "
            "нажми «Обновить».",
            wrap=True,
        )
        controls_layout.addWidget(hint)

        apply_button = QPushButton("Применить и перезапустить")
        apply_button.setObjectName("Primary")
        apply_button.clicked.connect(self._apply)
        controls_layout.addWidget(apply_button)

        restart = QPushButton("Перезапустить камеру")
        restart.setObjectName("Ghost")
        restart.clicked.connect(self.controller.restart_camera)
        controls_layout.addWidget(restart)

        controls_layout.addSpacing(4)
        controls_layout.addWidget(Divider())
        controls_layout.addWidget(kicker("Текущая камера"))
        self.device_info = muted("", wrap=True)
        controls_layout.addWidget(self.device_info)
        controls_layout.addWidget(
            muted(
                "640 × 480 — быстрее, 1280 × 720 — детальнее.",
                wrap=True,
            )
        )

        controls_layout.addStretch(1)
        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        controls_scroll.setWidget(controls)
        body.addWidget(controls_scroll, 2)
        root.addLayout(body, 1)

        self.camera_combo.currentIndexChanged.connect(self._update_device_info)
        self.reload_cameras()

        controller.previewReady.connect(self.preview.set_image)
        controller.statusReady.connect(self._on_status)
        controller.reportReady.connect(self._on_report)

    # --- список камер ----------------------------------------------------
    def reload_cameras(self) -> None:
        devices = list_cameras()
        self.camera_combo.clear()
        if devices:
            for device in devices:
                self.camera_combo.addItem(device.label, (device.name, device.index))
        else:
            for index in range(4):
                self.camera_combo.addItem(f"Камера {index}  ·  {index}", ("", index))

        saved_name = str(self.cfg["camera"].get("device_name", "")).strip()
        saved_index = int(self.cfg["camera"].get("index", 0))
        chosen = -1
        if saved_name:
            for position in range(self.camera_combo.count()):
                data = self.camera_combo.itemData(position)
                if data and str(data[0]).lower() == saved_name.lower():
                    chosen = position
                    break
        if chosen < 0:
            for position in range(self.camera_combo.count()):
                data = self.camera_combo.itemData(position)
                if data and int(data[1]) == saved_index:
                    chosen = position
                    break
        self.camera_combo.setCurrentIndex(max(0, chosen))
        self._update_device_info()

    def _update_device_info(self) -> None:
        data = self.camera_combo.currentData() or ("", 0)
        name, index = data
        text = f"{name or 'Камера без имени'}  ·  индекс {index}"
        self.device_info.setText(text)
        self.camera_combo.setToolTip(text)

    def _apply(self) -> None:
        data = self.camera_combo.currentData() or ("", 0)
        name, index = data
        width, height = self.resolution.currentData()
        self.cfg["camera"]["device_name"] = str(name)
        self.cfg["camera"]["index"] = int(index)
        self.cfg["camera"]["width"] = int(width)
        self.cfg["camera"]["height"] = int(height)
        self.cfg["camera"]["mirror"] = self.mirror.isChecked()
        self.cfg["camera"]["show_landmarks"] = self.landmarks.isChecked()
        self.cfg.setdefault("tracking", {})["max_hands"] = int(self.max_hands.currentData())
        self.controller.save()
        self.controller.log(
            f"Камера: {name or 'индекс ' + str(index)} · {width}×{height} · "
            f"рук: {self.max_hands.currentData()}"
        )
        self.controller.restart_camera()

    def _on_status(self, data: dict) -> None:
        if "fps" in data:
            fps = data.get("fps")
            self.chip_fps.setText(f"FPS {fps:.0f}" if isinstance(fps, (int, float)) else f"FPS {fps}")
        if "resolution" in data:
            self.chip_res.setText(str(data.get("resolution", "—")).replace("x", " × "))
        if "hands" in data:
            self.chip_hands.setText(f"РУКИ {data.get('hands', 0)}")

    def _on_report(self, report) -> None:
        hands = len(getattr(report, "hands", []) or [])
        self.chip_hands.setText(f"РУКИ {hands}")
        if report.hand is None:
            self.chip_gesture.setText("ЖЕСТ —")
            self.chip_fingers.setText("ПАЛЬЦЫ —")
            return
        gesture = report.state.gesture
        meta = get_gesture_meta(gesture, self.cfg) if gesture else None
        self.chip_gesture.setText(f"ЖЕСТ {meta['name'].upper() if meta else '—'}")
        self.chip_fingers.setText(f"ПАЛЬЦЫ {describe_fingers(report.hand.points)}")


    def refresh(self) -> None:
        self.reload_cameras()
        self.mirror.setChecked(bool(self.cfg["camera"].get("mirror", True)))
        self.landmarks.setChecked(bool(self.cfg["camera"].get("show_landmarks", True)))
        hands = int(self.cfg.get("tracking", {}).get("max_hands", 2))
        hand_index = self.max_hands.findData(hands)
        if hand_index >= 0:
            self.max_hands.setCurrentIndex(hand_index)
        size = (
            int(self.cfg["camera"].get("width", 640)),
            int(self.cfg["camera"].get("height", 480)),
        )
        size_index = self.resolution.findData(size)
        if size_index >= 0:
            self.resolution.setCurrentIndex(size_index)


class SettingsPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.cfg = controller.cfg
        self._loading = True
        self._build()
        self.refresh()
        self._loading = False

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        root.addLayout(page_header("Настройки", "Изменения сохраняются сразу."))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        columns = QHBoxLayout(container)
        columns.setContentsMargins(0, 4, 10, 8)
        columns.setSpacing(16)

        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(14)

        right_widget = QWidget()
        right_widget.setMinimumWidth(270)
        right_widget.setMaximumWidth(360)
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(14)

        columns.addWidget(left_widget, 3)
        columns.addWidget(right_widget, 2)

        engine_cfg = self.cfg["engine"]
        cursor_cfg = engine_cfg["cursor"]
        scroll_cfg = engine_cfg["scroll"]
        app_cfg = self.cfg["app"]

        # --- распознавание ---
        detect, detect_form = form_card(
            "Распознавание",
            "Чем больше стабилизация, тем реже ложные срабатывания, но тем медленнее отклик.",
        )
        self.stabilize = self._spin(2, 15, int(engine_cfg.get("stabilize_frames", 4)))
        detect_form.addRow("Стабилизация, кадров", self.stabilize)

        self.hold = self._spin(100, 1000, int(engine_cfg.get("hold_ms", 220)), " мс", 20)
        detect_form.addRow("Удержание жеста", self.hold)

        self.pair_hold = self._spin(
            100, 1500, int(engine_cfg.get("pair_hold_ms", 350)), " мс", 50
        )
        detect_form.addRow("Удержание двумя руками", self.pair_hold)

        self.cooldown = self._spin(200, 3000, int(engine_cfg.get("cooldown_ms", 700)), " мс", 50)
        detect_form.addRow("Пауза между действиями", self.cooldown)

        self.repeat = self._spin(200, 2000, int(engine_cfg.get("repeat_ms", 550)), " мс", 50)
        detect_form.addRow("Повтор громкости / яркости", self.repeat)

        self.drag_ms = self._spin(150, 1000, int(engine_cfg.get("drag_ms", 350)), " мс", 50)
        detect_form.addRow("Перетаскивание после", self.drag_ms)
        left.addWidget(detect)

        # --- курсор ---
        cursor, cursor_form = form_card(
            "Курсор и прокрутка",
            "Сглаживание убирает дрожь, но добавляет инерцию. Отступ от краёв кадра "
            "помогает не упираться в границы экрана.",
        )
        self.sensitivity = self._double(0.4, 2.0, float(cursor_cfg.get("sensitivity", 1.0)), 0.05)
        cursor_form.addRow("Чувствительность", self.sensitivity)

        self.smoothing = self._double(0.0, 0.95, float(cursor_cfg.get("smoothing", 0.55)), 0.05)
        cursor_form.addRow("Сглаживание", self.smoothing)

        self.margin = self._spin(0, 30, int(round(float(cursor_cfg.get("margin", 0.1)) * 100)), " %")
        cursor_form.addRow("Отступ от краёв кадра", self.margin)

        self.dead_zone = self._spin(0, 20, int(cursor_cfg.get("dead_zone", 2)), " px")
        cursor_form.addRow("Мёртвая зона", self.dead_zone)

        self.scroll_speed = self._double(0.3, 3.0, float(scroll_cfg.get("speed", 1.0)), 0.1)
        cursor_form.addRow("Скорость прокрутки", self.scroll_speed)

        self.invert_scroll = QCheckBox("Инвертировать направление")
        self.invert_scroll.setChecked(bool(scroll_cfg.get("invert", False)))
        cursor_form.addRow("", self.invert_scroll)
        left.addWidget(cursor)

        # --- приложение ---
        application, app_form = form_card("Приложение", "Пауза работает и в свёрнутом виде.")
        self.hotkey = HotkeyEdit()
        self.hotkey.set_combo(str(engine_cfg.get("pause_hotkey", "ctrl+alt+q")))
        app_form.addRow("Пауза / продолжить", self.hotkey)

        self.sounds = QCheckBox("Звуковой сигнал при действии")
        self.sounds.setChecked(bool(engine_cfg.get("sounds", False)))
        app_form.addRow("", self.sounds)

        self.autostart = QCheckBox("Запускать вместе с Windows")
        self.autostart.setChecked(bool(app_cfg.get("autostart", False)))
        app_form.addRow("", self.autostart)

        self.start_paused = QCheckBox("Запускать в паузе")
        self.start_paused.setChecked(bool(app_cfg.get("start_paused", False)))
        app_form.addRow("", self.start_paused)

        self.show_on_start = QCheckBox("Показывать окно при запуске")
        self.show_on_start.setChecked(bool(app_cfg.get("show_window_on_start", True)))
        app_form.addRow("", self.show_on_start)
        left.addWidget(application)

        # --- о программе ---
        about = Card()
        about_layout = QVBoxLayout(about)
        about_layout.setContentsMargins(20, 20, 20, 20)
        about_layout.setSpacing(6)

        logo = QLabel()
        logo.setObjectName("AboutLogo")
        logo.setPixmap(badge_pixmap(92))
        logo.setFixedSize(92, 92)
        about_layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignHCenter)

        version_label = kicker(f"Genis {__version__}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        about_layout.addWidget(version_label)

        about_title = QLabel("Управление жестами")
        about_title.setObjectName("H2")
        about_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        about_layout.addWidget(about_title)

        about_layout.addWidget(
            muted(
                "Камера обрабатывается локально, кадры никуда не отправляются. "
                "Настройки и записанные жесты лежат в %APPDATA%\\Genis.",
                wrap=True,
            )
        )

        made = QLabel("Сделано командой")
        made.setObjectName("Muted")
        made.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        about_layout.addSpacing(6)
        about_layout.addWidget(made)

        team = QLabel("CRAZY MONKEYS")
        team.setStyleSheet(
            f"color: {ACCENT}; font-weight: 800; font-size: 13px; letter-spacing: 1px;"
        )
        team.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        about_layout.addWidget(team)
        right.addWidget(about)

        # --- подсказки ---
        tips = Card()
        tips_layout = QVBoxLayout(tips)
        tips_layout.setContentsMargins(20, 18, 20, 18)
        tips_layout.setSpacing(8)
        tips_layout.addWidget(kicker("Подсказки"))
        for text in (
            "Ctrl+Alt+Q — пауза в любом приложении.",
            "Долгий щипок — перетаскивание, короткий — клик.",
            "Записывай жесты при том же свете, что и при работе.",
            "Если курсор дрожит — увеличь сглаживание.",
        ):
            line = muted(f"•  {text}", wrap=True)
            tips_layout.addWidget(line)
        right.addWidget(tips)
        right.addStretch(1)

        buttons = QHBoxLayout()
        open_folder = QPushButton("Открыть папку настроек")
        open_folder.setObjectName("Ghost")
        open_folder.clicked.connect(self._open_folder)
        reset = QPushButton("Сбросить всё")
        reset.setObjectName("Danger")
        reset.clicked.connect(self._reset)
        buttons.addWidget(open_folder)
        buttons.addStretch(1)
        buttons.addWidget(reset)
        left.addLayout(buttons)
        left.addStretch(1)

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        for widget in (
            self.stabilize,
            self.hold,
            self.pair_hold,
            self.cooldown,
            self.repeat,
            self.drag_ms,
            self.sensitivity,
            self.smoothing,
            self.margin,
            self.dead_zone,
            self.scroll_speed,
        ):
            widget.valueChanged.connect(self._changed)
        self.invert_scroll.toggled.connect(self._changed)
        self.sounds.toggled.connect(self._changed)
        self.start_paused.toggled.connect(self._changed)
        self.show_on_start.toggled.connect(self._changed)
        self.autostart.toggled.connect(self._autostart_changed)
        self.hotkey.textChanged.connect(self._changed)

    @staticmethod
    def _spin(
        minimum: int, maximum: int, value: int, suffix: str = "", step: int = 1
    ) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setSuffix(suffix)
        spin.setValue(max(minimum, min(maximum, value)))
        spin.setMaximumWidth(170)
        return spin

    @staticmethod
    def _double(
        minimum: float, maximum: float, value: float, step: float
    ) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setDecimals(2)
        spin.setValue(max(minimum, min(maximum, value)))
        spin.setMaximumWidth(170)
        return spin

    def _changed(self) -> None:
        if self._loading:
            return
        engine_cfg = self.cfg["engine"]
        engine_cfg["stabilize_frames"] = self.stabilize.value()
        engine_cfg["hold_ms"] = self.hold.value()
        engine_cfg["pair_hold_ms"] = self.pair_hold.value()
        engine_cfg["cooldown_ms"] = self.cooldown.value()
        engine_cfg["repeat_ms"] = self.repeat.value()
        engine_cfg["drag_ms"] = self.drag_ms.value()
        engine_cfg["cursor"]["sensitivity"] = round(self.sensitivity.value(), 2)
        engine_cfg["cursor"]["smoothing"] = round(self.smoothing.value(), 2)
        engine_cfg["cursor"]["margin"] = round(self.margin.value() / 100.0, 3)
        engine_cfg["cursor"]["dead_zone"] = self.dead_zone.value()
        engine_cfg["scroll"]["speed"] = round(self.scroll_speed.value(), 2)
        engine_cfg["scroll"]["invert"] = self.invert_scroll.isChecked()
        engine_cfg["sounds"] = self.sounds.isChecked()
        engine_cfg["pause_hotkey"] = self.hotkey.combo()

        self.cfg["app"]["start_paused"] = self.start_paused.isChecked()
        self.cfg["app"]["show_window_on_start"] = self.show_on_start.isChecked()

        self.controller.save()
        self.controller.reload_hotkey()

    def _autostart_changed(self, value: bool) -> None:
        if self._loading:
            return
        self.cfg["app"]["autostart"] = bool(value)
        self.controller.set_autostart(bool(value))
        self.controller.save()

    def _open_folder(self) -> None:
        try:
            os.startfile(data_dir())  # noqa: S606
        except OSError as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть папку: {exc}")

    def _reset(self) -> None:
        answer = QMessageBox.question(
            self,
            "Сбросить настройки",
            "Вернуть все настройки и привязки жестов к значениям по умолчанию?\n"
            "Записанные свои жесты тоже будут удалены.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.controller.reset_config()

    def refresh(self) -> None:
        self._loading = True
        engine_cfg = self.cfg["engine"]
        cursor_cfg = engine_cfg["cursor"]
        scroll_cfg = engine_cfg["scroll"]
        app_cfg = self.cfg["app"]

        self.stabilize.setValue(int(engine_cfg.get("stabilize_frames", 4)))
        self.hold.setValue(int(engine_cfg.get("hold_ms", 220)))
        self.pair_hold.setValue(int(engine_cfg.get("pair_hold_ms", 350)))
        self.cooldown.setValue(int(engine_cfg.get("cooldown_ms", 700)))
        self.repeat.setValue(int(engine_cfg.get("repeat_ms", 550)))
        self.drag_ms.setValue(int(engine_cfg.get("drag_ms", 350)))
        self.sensitivity.setValue(float(cursor_cfg.get("sensitivity", 1.0)))
        self.smoothing.setValue(float(cursor_cfg.get("smoothing", 0.55)))
        self.margin.setValue(int(round(float(cursor_cfg.get("margin", 0.1)) * 100)))
        self.dead_zone.setValue(int(cursor_cfg.get("dead_zone", 2)))
        self.scroll_speed.setValue(float(scroll_cfg.get("speed", 1.0)))
        self.invert_scroll.setChecked(bool(scroll_cfg.get("invert", False)))
        self.sounds.setChecked(bool(engine_cfg.get("sounds", False)))
        self.hotkey.set_combo(str(engine_cfg.get("pause_hotkey", "ctrl+alt+q")))
        self.start_paused.setChecked(bool(app_cfg.get("start_paused", False)))
        self.show_on_start.setChecked(bool(app_cfg.get("show_window_on_start", True)))
        self.autostart.setChecked(bool(app_cfg.get("autostart", False)))
        self._loading = False


__all__ = ["DashboardPage", "GesturesPage", "CameraPage", "SettingsPage"]

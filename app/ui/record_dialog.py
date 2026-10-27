"""Мастер записи собственного жеста."""

from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from ..config import new_id, now_iso
from ..core.actions import describe
from ..core.custom import build_pair_template, build_template, match_pair_score, match_score
from .action_dialog import ActionDialog
from .widgets import PreviewLabel

CAPTURE_SECONDS = 1.6
MIN_SAMPLES = 8


class RecordGestureDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.cfg = controller.cfg

        self.setWindowTitle("Запись своего жеста")
        self.setMinimumSize(760, 560)

        self.samples: list[Any] = []
        self.template: dict[str, Any] | None = None
        self.action: dict[str, Any] = {"type": "none", "params": {}}
        self._phase = "idle"
        self._pair_mode = False
        self._capture_started = 0.0
        self._countdown_left = 0
        self._test_score = 0.0

        self._build_ui()

        self._preview_conn = controller.previewReady.connect(self._on_preview)
        self._report_conn = controller.reportReady.connect(self._on_report)
        self.finished.connect(self._cleanup)
        controller.set_suspended(True)

    # --- UI --------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(12)

        title = QLabel("Свой жест")
        title.setObjectName("H1")
        root.addWidget(title)

        subtitle = QLabel(
            "Покажи жест в камеру и держи его ~1.5 секунды. Можно одной рукой "
            "или двумя: если в кадре обе руки — запишется двурукий жест. "
            "Записывай при том же свете и расстоянии, как будешь пользоваться."
        )
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(18)

        left = QVBoxLayout()
        self.preview = PreviewLabel("Ожидание камеры…")
        self.preview.setMinimumSize(440, 280)
        left.addWidget(self.preview, 1)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        left.addWidget(self.progress)
        self.status = QLabel("Нажми «Начать запись»")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        left.addWidget(self.status)
        body.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(10)

        name_label = QLabel("Название жеста")
        name_label.setObjectName("H2")
        right.addWidget(name_label)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Например: «Открыть Steam»")
        right.addWidget(self.name_edit)

        action_label = QLabel("Действие")
        action_label.setObjectName("H2")
        right.addWidget(action_label)
        self.action_button = QPushButton(describe(self.action))
        self.action_button.setObjectName("Ghost")
        self.action_button.clicked.connect(self._pick_action)
        right.addWidget(self.action_button)

        self.score_label = QLabel("Совпадение: —")
        self.score_label.setObjectName("Muted")
        right.addWidget(self.score_label)

        self.threshold_label = QLabel("")
        self.threshold_label.setObjectName("Mono")
        right.addWidget(self.threshold_label)

        right.addStretch(1)

        self.start_button = QPushButton("Начать запись")
        self.start_button.setObjectName("Primary")
        self.start_button.clicked.connect(self._start_countdown)
        right.addWidget(self.start_button)

        self.save_button = QPushButton("Сохранить жест")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save)
        right.addWidget(self.save_button)
        self.name_edit.textChanged.connect(self._update_save_state)

        cancel = QPushButton("Закрыть")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        right.addWidget(cancel)

        body.addLayout(right, 2)
        root.addLayout(body, 1)

    # --- поток записи ----------------------------------------------------
    def _start_countdown(self) -> None:
        if self._phase in ("countdown", "capture"):
            return
        self.samples.clear()
        self.template = None
        self._pair_mode = False
        self._phase = "countdown"
        self._countdown_left = 3
        self.start_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.progress.setValue(0)
        self.score_label.setText("Совпадение: —")
        self.threshold_label.setText("")
        self._tick_countdown()

    def _tick_countdown(self) -> None:
        if self._phase != "countdown":
            return
        if self._countdown_left > 0:
            self.status.setText(f"Приготовься… {self._countdown_left}")
            self.progress.setValue(int((3 - self._countdown_left) / 3 * 100))
            self._countdown_left -= 1
            QTimer.singleShot(800, self._tick_countdown)
            return

        self._phase = "capture"
        self._capture_started = time.perf_counter()
        self.samples.clear()
        self.status.setText("Держи жест…")
        self.progress.setValue(0)

    def _finish_capture(self) -> None:
        self._phase = "test"
        if len(self.samples) < MIN_SAMPLES:
            what = "обе руки" if self._pair_mode else "ладонь"
            self.status.setText(
                f"Рука почти не видна. Включи свет, покажи {what} в камеру и попробуй снова."
            )
            self.start_button.setEnabled(True)
            self.progress.setValue(0)
            self._phase = "idle"
            return

        try:
            self.template = (
                build_pair_template(self.samples)
                if self._pair_mode
                else build_template(self.samples)
            )
        except ValueError:
            self.status.setText("Не удалось построить шаблон. Попробуй ещё раз.")
            self.start_button.setEnabled(True)
            self._phase = "idle"
            return

        mode = "две руки" if self._pair_mode else "одна рука"
        self.threshold_label.setText(
            f"{mode} · кадров: {self.template['samples']} · "
            f"порог: {self.template['threshold']:.2f}"
        )
        self.status.setText("Готово! Теперь покажи жест — проверяем совпадение.")
        self.progress.setValue(0)
        self._update_save_state()
        self.start_button.setEnabled(True)
        self.start_button.setText("Записать заново")

    def _update_save_state(self) -> None:
        self.save_button.setEnabled(
            self.template is not None and bool(self.name_edit.text().strip())
        )

    # --- сигналы камеры --------------------------------------------------
    def _on_preview(self, image) -> None:
        self.preview.set_image(image)

    def _on_report(self, report) -> None:
        hands = list(getattr(report, "hands", []) or [])
        if not hands and report.hand is not None:
            hands = [report.hand]

        if not hands:
            if self._phase == "capture":
                self.status.setText("Не вижу руку — покажи ладонь в камеру")
            return

        if self._phase == "capture":
            if len(hands) >= 2 and not self.samples and not self._pair_mode:
                self._pair_mode = True

            if self._pair_mode:
                if len(hands) < 2:
                    self.status.setText(
                        "Веди обе руки в кадре — записываю жест двумя руками"
                    )
                    return
                self.samples.append(hands[:2])
                mode = "двумя руками"
            else:
                self.samples.append(hands[0].points.copy())
                mode = "одной рукой"

            elapsed = time.perf_counter() - self._capture_started
            percent = min(100, int(elapsed / CAPTURE_SECONDS * 100))
            self.progress.setValue(percent)
            self.status.setText(f"Держи жест {mode}…")
            if elapsed >= CAPTURE_SECONDS:
                self._finish_capture()

        elif self._phase == "test" and self.template is not None:
            if self._pair_mode:
                if len(hands) < 2:
                    self.score_label.setText("Совпадение: покажи обе руки")
                    return
                score = match_pair_score(
                    hands[:2], self.template["template"], self.template["threshold"]
                )
            else:
                score = match_score(
                    hands[0].points, self.template["template"], self.template["threshold"]
                )
            self._test_score = score
            percent = max(0, min(100, int(score * 100)))
            self.progress.setValue(percent)
            if score > 0:
                self.score_label.setText(f"Совпадение: {percent}%")
            else:
                self.score_label.setText("Совпадение: нет")

    # --- прочее ----------------------------------------------------------
    def _pick_action(self) -> None:
        dialog = ActionDialog(self.action, self.cfg, self, "Действие для нового жеста")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.action = dialog.action()
            self.action_button.setText(describe(self.action))

    def _save(self) -> None:
        if self.template is None:
            return
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setFocus()
            return
        self.cfg.setdefault("custom_gestures", []).append(
            {
                "id": new_id(),
                "name": name,
                "enabled": True,
                "hands": 2 if self._pair_mode else 1,
                "template": self.template["template"],
                "threshold": self.template["threshold"],
                "intra_distance": self.template.get("intra_distance", 0),
                "samples": self.template.get("samples", 0),
                "action": self.action,
                "created": now_iso(),
            }
        )
        self.controller.save()
        self.controller.log(
            f"Записан свой жест ({'две руки' if self._pair_mode else 'одна рука'}): "
            f"«{name}» → {describe(self.action)}"
        )
        self.accept()

    def _cleanup(self) -> None:
        try:
            self.controller.previewReady.disconnect(self._on_preview)
        except (RuntimeError, TypeError):
            pass
        try:
            self.controller.reportReady.disconnect(self._on_report)
        except (RuntimeError, TypeError):
            pass
        self.controller.set_suspended(False)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._cleanup()
        super().closeEvent(event)

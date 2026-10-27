"""Переиспользуемые виджеты интерфейса."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QKeyEvent, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..config import get_gesture_meta  # noqa: F401  (реэкспорт для страниц)
from .theme import BORDER, MUTED_DIM, PREVIEW_BG


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, name: str = "Card"):
        super().__init__(parent)
        self.setObjectName(name)


class HeroCard(Card):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, "HeroCard")


class Divider(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Divider")
        self.setFixedHeight(1)


class Chip(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("Chip")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class StatusPill(QLabel):
    def __init__(self, text: str = "Выключено", state: str = "off", parent=None):
        super().__init__(text, parent)
        self.setObjectName("StatusPill")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_state(state, text)

    def set_state(self, state: str, text: str | None = None) -> None:
        if text is not None:
            self.setText(text)
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)


class PreviewLabel(QWidget):
    """Круглое превью камеры с заглушкой, когда сигнала нет."""

    def __init__(self, placeholder: str = "Камера выключена", parent=None):
        super().__init__(parent)
        self._placeholder = placeholder
        self._image: QImage | None = None
        self.setMinimumSize(320, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_image(self, image: QImage) -> None:
        self._image = image
        self.update()

    def clear_image(self) -> None:
        self._image = None
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)

        painter.fillPath(path, QColor(PREVIEW_BG))
        if self._image is not None and not self._image.isNull():
            painter.save()
            painter.setClipPath(path)
            source = self._image
            target = rect
            scale = min(
                target.width() / max(1, source.width()),
                target.height() / max(1, source.height()),
            )
            draw_w = source.width() * scale
            draw_h = source.height() * scale
            painter.drawImage(
                QRectF(
                    target.center().x() - draw_w / 2,
                    target.center().y() - draw_h / 2,
                    draw_w,
                    draw_h,
                ),
                source,
            )
            painter.restore()
        else:
            painter.setPen(QColor(MUTED_DIM))
            font = painter.font()
            font.setPixelSize(12)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._placeholder)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor(BORDER))
        painter.drawPath(path)


class StatBlock(QWidget):
    def __init__(self, label: str, value: str = "—", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("StatValue")
        caption = QLabel(label.upper())
        caption.setObjectName("StatLabel")
        layout.addWidget(self.value_label)
        layout.addWidget(caption)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class HotkeyEdit(QLineEdit):
    """Поле, которое записывает нажатую комбинацию клавиш."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Нажмите комбинацию…")
        self.setToolTip("Кликните в поле и нажмите нужные клавиши")

    def set_combo(self, combo: str) -> None:
        self.setText((combo or "").upper())

    def combo(self) -> str:
        return self.text().lower()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        if key in (
            Qt.Key.Key_Control,
            Qt.Key.Key_Shift,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Meta,
        ):
            event.accept()
            return
        if key == Qt.Key.Key_Escape:
            self.clear()
            event.accept()
            return

        modifiers: list[str] = []
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            modifiers.append("ctrl")
        if mods & Qt.KeyboardModifier.AltModifier:
            modifiers.append("alt")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("shift")
        if mods & Qt.KeyboardModifier.MetaModifier:
            modifiers.append("win")

        name = self._key_name(event)
        if name is None:
            event.accept()
            return
        if name in ("ctrl", "alt", "shift", "win"):
            event.accept()
            return
        if name in modifiers:
            modifiers.remove(name)
        self.setText("+".join(modifiers + [name]).upper())
        event.accept()

    @staticmethod
    def _key_name(event: QKeyEvent) -> str | None:
        key = event.key()
        special = {
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Insert: "insert",
            Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end",
            Qt.Key.Key_PageUp: "pageup",
            Qt.Key.Key_PageDown: "pagedown",
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_Down: "down",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_Print: "printscreen",
        }
        if key in special:
            return special[key]
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F20:
            return f"f{key - Qt.Key.Key_F1 + 1}"
        text = (event.text() or "").strip()
        if text and text.isprintable():
            return text.lower()
        return None


class StatRow(QWidget):
    """Строка «подпись — значение»."""

    def __init__(self, label: str, value: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        caption = QLabel(label)
        caption.setObjectName("Muted")
        self.value = QLabel(value)
        self.value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(caption)
        layout.addStretch(1)
        layout.addWidget(self.value)


class BrandBlock(QWidget):
    """Логотип, название и подпись «команда Crazy Monkeys»."""

    def __init__(self, parent=None, compact: bool = False):
        super().__init__(parent)
        from .logo import monkey_pixmap

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(10)
        icon_size = 26 if compact else 34
        icon = QLabel()
        icon.setPixmap(monkey_pixmap(icon_size))
        icon.setFixedSize(icon_size, icon_size)
        row.addWidget(icon)

        titles = QVBoxLayout()
        titles.setSpacing(1)
        name = QLabel("Genis")
        name.setObjectName("Brand")
        titles.addWidget(name)
        if not compact:
            subtitle = QLabel("GESTURE CONTROL")
            subtitle.setObjectName("BrandSub")
            titles.addWidget(subtitle)
        titles.addStretch(1)
        row.addLayout(titles)
        row.addStretch(1)
        layout.addLayout(row)
        self.setMinimumHeight(34 if compact else 44)

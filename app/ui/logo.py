"""Пиксельный логотип: обезьяна команды Crazy Monkeys.

Рисуется кодом из сетки 16×16, поэтому остаётся чётким на любом размере —
от значка в трее 16 px до иконки приложения 256 px.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap

# Палитра бренда
BG_DEEP = "#050907"
BG_PANEL = "#0B1410"
BG_RAISED = "#101C15"
BORDER = "#1B2C21"
BORDER_LIGHT = "#27412F"
TEXT = "#E9F6EE"
MUTED = "#8AA894"
ACCENT = "#35F08A"
ACCENT_SOFT = "#0F2A1B"
ACCENT_DIM = "#1FBF63"
ACCENT_BRIGHT = "#8CFFC0"
DARK_INK = "#04120A"

MONKEY = [
    "                ",
    "     ######     ",
    "   ##########   ",
    "  ############  ",
    " ############## ",
    " ##==========## ",
    "@@#==..==..==#@@",
    "@@#==..==..==#@@",
    " ##==========## ",
    " ##===....===## ",
    " ##===....===## ",
    "  ##========##  ",
    "   ##########   ",
    "    ########    ",
    "     ######     ",
    "                ",
]

PIXELS = {
    "#": ACCENT_DIM,
    "@": ACCENT_BRIGHT,
    "=": "#9BF7C2",
    ".": "#06120B",
}

GRID = 16


def _draw_monkey(painter: QPainter, x: float, y: float, cell: float) -> None:
    for row, line in enumerate(MONKEY):
        for col, symbol in enumerate(line):
            color = PIXELS.get(symbol)
            if color is None:
                continue
            painter.fillRect(
                QRectF(x + col * cell, y + row * cell, cell, cell), QColor(color)
            )


def _monkey_image(cell: int = 16) -> QImage:
    image = QImage(GRID * cell, GRID * cell, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    _draw_monkey(painter, 0, 0, cell)
    painter.end()
    return image


_BASE_IMAGE: QImage | None = None


def _base_image() -> QImage:
    global _BASE_IMAGE
    if _BASE_IMAGE is None:
        _BASE_IMAGE = _monkey_image(16)
    return _BASE_IMAGE


def _scaled_monkey(size: int) -> QImage:
    return _base_image().scaled(
        max(1, int(size)),
        max(1, int(size)),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )


def monkey_pixmap(size: int = 64) -> QPixmap:
    """Обезьяна без фона."""
    return QPixmap.fromImage(_scaled_monkey(size))


def badge_pixmap(size: int = 256, rounded: bool = True) -> QPixmap:
    """Иконка приложения: тёмный скруглённый квадрат с обезьяной."""
    size = max(16, int(size))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    radius = size * 0.24
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(BG_PANEL))
    if rounded:
        painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)
    else:
        painter.drawRect(QRectF(0, 0, size, size))

    painter.setBrush(Qt.BrushStyle.NoBrush)
    pen = painter.pen()
    pen.setColor(QColor(BORDER_LIGHT))
    pen.setWidthF(max(1.0, size * 0.012))
    painter.setPen(pen)
    inset = max(1.0, size * 0.02)
    if rounded:
        painter.drawRoundedRect(
            QRectF(inset, inset, size - 2 * inset, size - 2 * inset),
            radius - inset,
            radius - inset,
        )
    else:
        painter.drawRect(QRectF(inset, inset, size - 2 * inset, size - 2 * inset))

    inner = max(8, int(round(size * 0.74)))
    monkey = _scaled_monkey(inner)
    painter.drawImage(
        int(round((size - monkey.width()) / 2)),
        int(round((size - monkey.height()) / 2)),
        monkey,
    )
    painter.end()
    return pixmap


def circle_pixmap(size: int = 64, dot: str | None = None) -> QPixmap:
    """Значок трея: круг с обезьяной и точкой состояния."""
    size = max(16, int(size))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(BG_PANEL))
    painter.drawEllipse(QRectF(1, 1, size - 2, size - 2))

    inner = max(8, int(round(size * 0.82)))
    monkey = _scaled_monkey(inner)
    painter.drawImage(
        int(round((size - monkey.width()) / 2)),
        int(round((size - monkey.height()) / 2)),
        monkey,
    )

    if dot:
        radius = max(3, int(size * 0.19))
        margin = max(1, int(size * 0.03))
        painter.setBrush(QColor(dot))
        painter.setPen(QColor(BG_PANEL))
        painter.drawEllipse(
            QRectF(size - radius * 2 - margin, size - radius * 2 - margin,
                   radius * 2, radius * 2)
        )
    painter.end()
    return pixmap


def icon_from(pixmap_factory, sizes=(16, 20, 24, 32, 40, 48, 64, 128, 256)) -> QIcon:
    icon = QIcon()
    for size in sizes:
        icon.addPixmap(pixmap_factory(size))
    return icon


def app_icon() -> QIcon:
    return icon_from(lambda size: badge_pixmap(size))


def tray_icon(active: bool = True, paused: bool = False, error: bool = False) -> QIcon:
    dot = ACCENT if active and not paused and not error else None
    if error:
        dot = "#FF6B6B"
    elif paused:
        dot = "#F5C451"
    return icon_from(lambda size: circle_pixmap(size, dot), sizes=(16, 20, 24, 32, 48, 64))


def logo_bytes_png(size: int = 512) -> bytes:
    """PNG для README и установщика."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    badge_pixmap(size).save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def logo_image(size: int = 512) -> QImage:
    return badge_pixmap(size).toImage()


__all__ = [
    "app_icon",
    "tray_icon",
    "badge_pixmap",
    "monkey_pixmap",
    "circle_pixmap",
    "logo_bytes_png",
    "logo_image",
]

"""Генерация ресурсов бренда: иконки интерфейса, логотип, .ico для сборки.

Запуск: .venv\\Scripts\\python.exe tools\\make_assets.py
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.ui.logo import MONKEY, PIXELS, badge_pixmap  # noqa: E402

ASSETS = ROOT / "assets"
ICONS = ASSETS / "icons"


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def chevron(direction: str, size: int = 24, color: str = "#8AA894") -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(size * 0.14)
    pen.setCapStyle(pen.capStyle().RoundCap)
    pen.setJoinStyle(pen.joinStyle().RoundJoin)
    painter.setPen(pen)
    margin = size * 0.3
    if direction == "down":
        points = [QPointF(margin, size * 0.4), QPointF(size / 2, size * 0.62),
                  QPointF(size - margin, size * 0.4)]
    else:
        points = [QPointF(margin, size * 0.62), QPointF(size / 2, size * 0.4),
                  QPointF(size - margin, size * 0.62)]
    painter.drawPolyline(QPolygonF(points))
    painter.end()
    return image


def checkmark(size: int = 28) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#04120A"))
    pen.setWidthF(size * 0.16)
    pen.setCapStyle(pen.capStyle().RoundCap)
    pen.setJoinStyle(pen.joinStyle().RoundJoin)
    painter.setPen(pen)
    points = [
        QPointF(size * 0.22, size * 0.52),
        QPointF(size * 0.42, size * 0.72),
        QPointF(size * 0.78, size * 0.3),
    ]
    painter.drawPolyline(QPolygonF(points))
    painter.end()
    return image


def write_ico(path: Path, sizes=(16, 24, 32, 48, 64, 128, 256)) -> None:
    images = []
    for size in sizes:
        images.append((size, png_bytes(badge_pixmap(size).toImage())))

    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    payload = b""
    for size, data in images:
        width = 0 if size >= 256 else size
        entries += struct.pack(
            "<BBBBHHII", width, width, 0, 0, 1, 32, len(data), offset
        )
        payload += data
        offset += len(data)
    path.write_bytes(header + entries + payload)


def svg_logo() -> str:
    size = 16
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320" '
        'width="320" height="320" shape-rendering="crispEdges">',
        '<rect width="320" height="320" rx="76" fill="#0B1410"/>',
        '<rect x="6" y="6" width="308" height="308" rx="70" fill="none" '
        'stroke="#27412F" stroke-width="3"/>',
    ]
    cell = 18
    offset = (320 - cell * size) / 2
    for row, line in enumerate(MONKEY):
        for col, symbol in enumerate(line):
            color = PIXELS.get(symbol)
            if color is None:
                continue
            lines.append(
                f'<rect x="{offset + col * cell:.0f}" y="{offset + row * cell:.0f}" '
                f'width="{cell}" height="{cell}" fill="{color}"/>'
            )
    lines.append("</svg>")
    return "\n".join(lines)


def main() -> int:
    app = QApplication(sys.argv)  # noqa: F841
    ICONS.mkdir(parents=True, exist_ok=True)

    chevron("down").save(str(ICONS / "chevron-down.png"))
    chevron("up").save(str(ICONS / "chevron-up.png"))
    checkmark().save(str(ICONS / "check.png"))

    (ASSETS / "logo.svg").write_text(svg_logo(), encoding="utf-8")
    badge_pixmap(512).save(str(ASSETS / "logo.png"))
    write_ico(ASSETS / "genis.ico")

    for path in sorted(ASSETS.glob("*")) + sorted(ICONS.glob("*")):
        if path.is_file():
            print(f"{path.relative_to(ROOT)}  {path.stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

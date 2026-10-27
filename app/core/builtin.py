"""Классификация встроенных жестов по геометрии руки."""

from __future__ import annotations

import numpy as np

from .features import (
    INDEX_TIP,
    MIDDLE_TIP,
    PINKY_MCP,
    THUMB_MCP,
    THUMB_TIP,
    WRIST,
    finger_extension,
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def classify(points: np.ndarray) -> tuple[str, float]:
    """Определяет жест по 21 точке. Возвращает (id, уверенность 0..1)."""
    pts = np.asarray(points, dtype=np.float32)
    ext, thumb_ext, palm = finger_extension(pts)

    pinch_ratio = float(np.linalg.norm(pts[THUMB_TIP] - pts[INDEX_TIP])) / palm
    index_reach = float(np.linalg.norm(pts[INDEX_TIP] - pts[WRIST])) / palm

    # «ОК»: указательный согнут и касается большого, остальные три вытянуты.
    if pinch_ratio < 0.45 and ext[1] and ext[2] and ext[3] and not ext[0]:
        return "ok", _clamp(1.0 - pinch_ratio / 0.45, 0.55, 1.0)

    # Щипок: подушечки рядом, но указательный при этом не прижат к ладони
    # (иначе обычный кулак определялся бы как щипок).
    if pinch_ratio < 0.38 and index_reach > 1.0:
        return "pinch", _clamp(1.0 - pinch_ratio / 0.38, 0.55, 1.0)

    if not any(ext):
        if thumb_ext:
            dy = (pts[WRIST][1] - pts[THUMB_TIP][1]) / palm
            if dy > 0.35:
                return "thumbs_up", _clamp(dy / 1.2, 0.55, 1.0)
            if dy < -0.35:
                return "thumbs_down", _clamp(-dy / 1.2, 0.55, 1.0)
        return "fist", 0.85

    # Рок: указательный и мизинец вверх, средний и безымянный сжаты.
    if ext[0] and not ext[1] and not ext[2] and ext[3]:
        return "rock", 0.8

    if ext[0] and not ext[1] and not ext[2] and not ext[3]:
        # «Пистолет» / жест указательным пальцем с отведённым большим
        # тоже считаем указательным — курсор важнее.
        conf = 0.9 if not thumb_ext else 0.78
        return "point", conf

    if ext[0] and ext[1] and not ext[2] and not ext[3]:
        return "peace", 0.88

    if ext[0] and ext[1] and ext[2] and not ext[3]:
        return "three", 0.86

    if all(ext):
        return ("open_palm", 0.9) if thumb_ext else ("four", 0.8)

    # Смешанные состояния — самое близкое: считаем кулаком.
    return "fist", 0.5


def describe_fingers(points: np.ndarray) -> str:
    ext, thumb, _ = finger_extension(points)
    names = ["указ.", "сред.", "безым.", "миз."]
    up = [n for n, e in zip(names, ext) if e]
    if thumb:
        up.insert(0, "больш.")
    return ", ".join(up) if up else "все сжаты"


# Комбинации одиночных жестов, которые считаются жестом двумя руками.
PAIR_COMBOS: dict[tuple[str, str], str] = {
    ("fist", "fist"): "two_fists",
    ("open_palm", "open_palm"): "two_open_palms",
    ("pinch", "pinch"): "two_pinches",
}


def classify_pair(first: str | None, second: str | None) -> str | None:
    """Жест двумя руками по жестам каждой руки (порядок не важен)."""
    if not first or not second:
        return None
    return PAIR_COMBOS.get(tuple(sorted((first, second))))

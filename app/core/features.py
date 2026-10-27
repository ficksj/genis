"""Работа с точками руки: канонизация и признаки для сравнения жестов."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

NUM_LANDMARKS = 21

# Индексы MediaPipe Hand Landmarker
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

# Связи между точками — для отрисовки скелета на превью.
HAND_CONNECTIONS: tuple[tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
)


@dataclass
class Hand:
    """Одна обнаруженная рука в координатах кадра (пиксели)."""

    points: np.ndarray              # (21, 3) float32
    width: int
    height: int
    handedness: str = ""            # "Left" / "Right" от MediaPipe (справочно)
    score: float = 1.0

    @property
    def palm_size(self) -> float:
        return float(np.linalg.norm(self.points[MIDDLE_MCP] - self.points[WRIST]))

    @property
    def center(self) -> np.ndarray:
        return self.points[[WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]].mean(axis=0)

    @property
    def index_tip(self) -> np.ndarray:
        return self.points[INDEX_TIP]


def points_from_landmarks(landmarks, width: int, height: int) -> np.ndarray:
    """NormalizedLandmark (0..1) -> пиксельные координаты с сохранением пропорций.

    z тоже переводим в пиксели (по ширине кадра), чтобы признаки не зависели
    от соотношения сторон кадра.
    """
    pts = np.empty((NUM_LANDMARKS, 3), dtype=np.float32)
    for i, lm in enumerate(landmarks):
        pts[i, 0] = float(lm.x) * width
        pts[i, 1] = float(lm.y) * height
        pts[i, 2] = float(getattr(lm, "z", 0.0)) * width
    return pts


def canonical(points: np.ndarray) -> np.ndarray:
    """Инвариант к положению, размеру и стороне руки (левая/правая).

    - переносим начало координат в запястье;
    - отражаем по X, чтобы левая рука выглядела как правая;
    - масштабируем по размеру ладони (запястье -> основание среднего пальца).
    """
    pts = np.asarray(points, dtype=np.float32).copy()
    if pts.shape != (NUM_LANDMARKS, 3):
        raise ValueError(f"Ожидалось (21, 3), получено {pts.shape}")
    pts -= pts[WRIST]

    v_mid = pts[MIDDLE_MCP]
    v_pinky = pts[PINKY_MCP]
    cross = float(v_mid[0] * v_pinky[1] - v_mid[1] * v_pinky[0])
    if cross < 0:
        pts[:, 0] *= -1.0

    scale = float(np.linalg.norm(pts[MIDDLE_MCP]))
    if scale < 1e-6:
        scale = 1.0
    return pts / scale


def feature_vector(points: np.ndarray) -> np.ndarray:
    """Вектор признаков (63 числа) для сравнения с шаблонами своих жестов."""
    return canonical(points).reshape(-1).astype(np.float32)


def order_pair(hands: list["Hand"]) -> tuple["Hand", "Hand"]:
    """Упорядочивает руки слева направо — независимо от порядка от MediaPipe."""
    first, second = hands[0], hands[1]
    if float(first.points[WRIST][0]) <= float(second.points[WRIST][0]):
        return first, second
    return second, first


def pair_feature_vector(hands: list["Hand"]) -> np.ndarray:
    """Вектор для жеста двумя руками: 63 + 63 + расстояние между запястьями.

    Каждая рука нормализуется отдельно (размер, поворот, сторона), а взаимное
    положение сохраняется: dx и dy делятся на средний размер ладони. Порядок
    рук фиксирован слева направо, поэтому зеркало камеры не ломает шаблон.
    """
    if len(hands) < 2:
        raise ValueError("Для жеста двумя руками нужны две руки")
    left, right = order_pair(hands)
    palm = (left.palm_size + right.palm_size) / 2.0
    if palm < 1e-6:
        palm = 1.0
    dx = float(right.points[WRIST][0] - left.points[WRIST][0]) / palm
    dy = float(right.points[WRIST][1] - left.points[WRIST][1]) / palm
    return np.concatenate(
        [
            feature_vector(left.points),
            feature_vector(right.points),
            np.asarray([dx, dy], dtype=np.float32),
        ]
    ).astype(np.float32)


def dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(a) - np.asarray(b)))


def finger_extension(points: np.ndarray) -> tuple[list[bool], bool, float]:
    """Возвращает (вытянутость 4 пальцев, вытянут ли большой, размер ладони)."""
    pts = np.asarray(points, dtype=np.float32)
    palm = float(np.linalg.norm(pts[MIDDLE_MCP] - pts[WRIST]))
    if palm < 1e-6:
        palm = 1.0

    extended: list[bool] = []
    for mcp, pip, dip, tip in (
        (INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP),
        (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
        (RING_MCP, RING_PIP, RING_DIP, RING_TIP),
        (PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP),
    ):
        a = pts[pip] - pts[mcp]
        b = pts[tip] - pts[pip]
        denom = float(np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
        cos = float(np.dot(a, b) / denom)
        farther = float(np.linalg.norm(pts[tip] - pts[WRIST])) > (
            float(np.linalg.norm(pts[pip] - pts[WRIST])) * 1.08
        )
        extended.append(bool(cos > 0.25 and farther))

    thumb_extended = float(np.linalg.norm(pts[THUMB_TIP] - pts[PINKY_MCP])) > (
        float(np.linalg.norm(pts[THUMB_MCP] - pts[PINKY_MCP])) * 1.15
    )
    return extended, bool(thumb_extended), palm

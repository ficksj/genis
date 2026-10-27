"""Свои жесты: запись шаблона и сравнение с ним.

Шаблон хранится как вектор признаков. Для одной руки — 63 числа, для двух —
126 чисел плюс взаимное положение запястий. Тип шаблона фиксируется полем
``hands`` (1 или 2), чтобы однорукие и двурукие жесты не сравнивались между собой.
"""

from __future__ import annotations

import numpy as np

from .features import feature_vector, pair_feature_vector


def build_template_from_vectors(vectors: list[np.ndarray]) -> dict:
    if not vectors:
        raise ValueError("Нет кадров для шаблона")
    features = np.stack([np.asarray(v, dtype=np.float32) for v in vectors])
    mean = features.mean(axis=0)
    intra = float(np.linalg.norm(features - mean, axis=1).mean())

    # Порог: насколько «размыт» жест при записи + запас.
    threshold = float(np.clip(intra * 2.8 + 0.08, 0.20, 0.75))
    return {
        "template": mean.round(6).tolist(),
        "threshold": round(threshold, 4),
        "intra_distance": round(intra, 4),
        "samples": int(features.shape[0]),
    }


def build_template(points_list: list[np.ndarray]) -> dict:
    """Шаблон жеста одной рукой."""
    return build_template_from_vectors([feature_vector(p) for p in points_list])


def build_pair_template(hands_list: list[list]) -> dict:
    """Шаблон жеста двумя руками (каждый кадр — список из двух Hand)."""
    return build_template_from_vectors([pair_feature_vector(hands) for hands in hands_list])


def score_vector(vec: np.ndarray, template: list[float], threshold: float) -> float:
    """1.0 — идеальное совпадение, 0.0 — на границе порога, <0 — не совпало."""
    vec = np.asarray(vec, dtype=np.float32)
    tpl = np.asarray(template, dtype=np.float32)
    if tpl.shape[0] != vec.shape[0]:
        return -1.0
    distance = float(np.linalg.norm(vec - tpl))
    if threshold <= 1e-6:
        threshold = 0.3
    return 1.0 - distance / threshold


def match_score(points: np.ndarray, template: list[float], threshold: float) -> float:
    return score_vector(feature_vector(points), template, threshold)


def match_pair_score(hands: list, template: list[float], threshold: float) -> float:
    try:
        vector = pair_feature_vector(hands)
    except ValueError:
        return -1.0
    return score_vector(vector, template, threshold)


def _best_match(
    vector: np.ndarray | None, gestures: list[dict], required_hands: int
) -> tuple[str, float] | None:
    if vector is None:
        return None
    best: tuple[str, float] | None = None
    for gesture in gestures:
        if not gesture.get("enabled", True):
            continue
        if int(gesture.get("hands", 1)) != required_hands:
            continue
        template = gesture.get("template")
        if not template:
            continue
        score = score_vector(vector, template, float(gesture.get("threshold", 0.3)))
        if score <= 0:
            continue
        if best is None or score > best[1]:
            best = (gesture["id"], score)
    return best


def best_custom_match(
    points: np.ndarray, gestures: list[dict]
) -> tuple[str, float] | None:
    """Лучший свой жест одной рукой: (id, score) или None."""
    return _best_match(feature_vector(points), gestures, required_hands=1)


def best_pair_match(hands: list, gestures: list[dict]) -> tuple[str, float] | None:
    """Лучший свой жест двумя руками: (id, score) или None."""
    if len(hands) < 2:
        return None
    return _best_match(pair_feature_vector(hands), gestures, required_hands=2)

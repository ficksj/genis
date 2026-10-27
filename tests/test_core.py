"""Тесты ядра: признаки, классификатор, свои жесты, конфиг, движок."""

from __future__ import annotations

import json
import random
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import BUILTIN_GESTURES, default_config, load_config, save_config  # noqa: E402
from app.core import engine as engine_module  # noqa: E402
from app.core.builtin import classify, classify_pair  # noqa: E402
from app.core.cameras import CameraDevice, resolve_index  # noqa: E402
from app.core.custom import (  # noqa: E402
    best_custom_match,
    best_pair_match,
    build_pair_template,
    build_template,
    match_pair_score,
    match_score,
)
from app.core.engine import GestureEngine  # noqa: E402
from app.core.hotkey import (  # noqa: E402
    MOD_ALT,
    MOD_CONTROL,
    MOD_NOREPEAT,
    MOD_SHIFT,
    MOD_WIN,
    GlobalHotkey,
    parse_combo,
    pretty_combo,
)
from app.core.features import (  # noqa: E402
    Hand,
    canonical,
    feature_vector,
    finger_extension,
    pair_feature_vector,
)

WRIST = (0.5, 0.9)
MCPS = ((0.42, 0.62), (0.50, 0.60), (0.58, 0.62), (0.66, 0.66))


def make_hand(
    fingers: tuple[bool, bool, bool, bool] = (False, False, False, False),
    thumb: str = "folded",
    pinch: bool = False,
    mirror: bool = False,
    scale: float = 1.0,
    offset: tuple[float, float] = (0.0, 0.0),
) -> np.ndarray:
    """Синтетическая рука в 2D: удобно для проверки правил классификатора."""
    pts = np.zeros((21, 3), dtype=np.float32)
    pts[0] = (WRIST[0], WRIST[1], 0.0)

    for finger_index, (extended, mcp) in enumerate(zip(fingers, MCPS)):
        base = 5 + finger_index * 4
        mcp_pt = np.array([mcp[0], mcp[1], 0.0], dtype=np.float32)
        pts[base] = mcp_pt
        if extended:
            pip = mcp_pt + np.array([0.0, -0.10, 0.0], dtype=np.float32)
            dip = pip + np.array([0.0, -0.085, 0.0], dtype=np.float32)
            tip = dip + np.array([0.0, -0.07, 0.0], dtype=np.float32)
        else:
            pip = mcp_pt + np.array([0.0, -0.08, 0.0], dtype=np.float32)
            dip = pip + np.array([0.02, 0.065, 0.0], dtype=np.float32)
            tip = dip + np.array([0.015, 0.055, 0.0], dtype=np.float32)
        pts[base + 1] = pip
        pts[base + 2] = dip
        pts[base + 3] = tip

    pts[1] = (0.40, 0.84, 0.0)
    pts[2] = (0.35, 0.78, 0.0)
    pts[3] = (0.30, 0.72, 0.0)
    thumb_tips = {
        "folded": (0.44, 0.74),
        "out": (0.24, 0.66),
        "up": (0.26, 0.48),
        "down": (0.26, 1.12),
        "pinch": (float(pts[8][0]) + 0.03, float(pts[8][1]) + 0.02),
    }
    pts[4] = (*thumb_tips.get(thumb, thumb_tips["folded"]), 0.0)

    if mirror:
        pts[:, 0] = 1.0 - pts[:, 0]
    if scale != 1.0:
        center = np.array([0.5, 0.75], dtype=np.float32)
        pts[:, :2] = (pts[:, :2] - center) * scale + center
    pts[:, 0] += offset[0]
    pts[:, 1] += offset[1]
    return pts


def add_noise(points: np.ndarray, sigma: float = 0.004, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noisy = points.copy()
    noisy[:, :2] += rng.normal(0, sigma, (21, 2)).astype(np.float32)
    return noisy


def to_pixels(points: np.ndarray, width: int = 640, height: int = 480) -> np.ndarray:
    """Переводит нормализованную руку в пиксели — так же, как это делает камера."""
    return points * np.array([width, height, width], dtype=np.float32)


class ClassifierTests(unittest.TestCase):
    def test_point(self):
        gesture, conf = classify(make_hand((True, False, False, False)))
        self.assertEqual(gesture, "point")
        self.assertGreater(conf, 0.5)

    def test_fist(self):
        gesture, _ = classify(make_hand((False, False, False, False)))
        self.assertEqual(gesture, "fist")

    def test_open_palm(self):
        gesture, _ = classify(make_hand((True, True, True, True), thumb="out"))
        self.assertEqual(gesture, "open_palm")

    def test_four(self):
        gesture, _ = classify(make_hand((True, True, True, True), thumb="folded"))
        self.assertEqual(gesture, "four")

    def test_peace(self):
        gesture, _ = classify(make_hand((True, True, False, False)))
        self.assertEqual(gesture, "peace")

    def test_three(self):
        gesture, _ = classify(make_hand((True, True, True, False)))
        self.assertEqual(gesture, "three")

    def test_rock(self):
        gesture, _ = classify(make_hand((True, False, False, True)))
        self.assertEqual(gesture, "rock")

    def test_thumbs_up(self):
        gesture, _ = classify(make_hand((False, False, False, False), thumb="up"))
        self.assertEqual(gesture, "thumbs_up")

    def test_thumbs_down(self):
        gesture, _ = classify(make_hand((False, False, False, False), thumb="down"))
        self.assertEqual(gesture, "thumbs_down")

    def test_pinch(self):
        gesture, _ = classify(make_hand((True, False, False, False), thumb="pinch"))
        self.assertEqual(gesture, "pinch")

    def test_ok(self):
        gesture, _ = classify(
            make_hand((False, True, True, True), thumb="pinch")
        )
        self.assertEqual(gesture, "ok")

    def test_fist_thumb_near_index_is_not_pinch(self):
        # Регрессия: в кулаке кончик большого пальца рядом со скрученным
        # указательным — раньше это ошибочно считалось щипком.
        gesture, _ = classify(make_hand((False, False, False, False), thumb="folded"))
        self.assertNotEqual(gesture, "pinch")


class FeatureTests(unittest.TestCase):
    def test_translation_and_scale_invariance(self):
        base = feature_vector(make_hand((True, False, False, False)))
        moved = feature_vector(
            make_hand((True, False, False, False), scale=1.4, offset=(0.2, -0.1))
        )
        self.assertLess(float(np.linalg.norm(base - moved)), 0.05)

    def test_mirror_invariance(self):
        right = feature_vector(make_hand((True, True, False, False)))
        left = feature_vector(make_hand((True, True, False, False), mirror=True))
        self.assertLess(float(np.linalg.norm(right - left)), 0.05)

    def test_hand_wrapper(self):
        points = make_hand((True, False, False, False))
        hand = Hand(points=points * 100, width=640, height=480)
        self.assertGreater(hand.palm_size, 0)
        self.assertEqual(hand.points.shape, (21, 3))

    def test_finger_extension(self):
        ext, thumb, palm = finger_extension(make_hand((True, False, False, False)))
        self.assertEqual(ext, [True, False, False, False])
        self.assertFalse(thumb)
        self.assertGreater(palm, 0)


class CustomGestureTests(unittest.TestCase):
    def test_template_matches_itself(self):
        samples = [
            to_pixels(make_hand((True, True, False, False), thumb="out")) for _ in range(10)
        ]
        template = build_template(samples)
        score = match_score(
            to_pixels(make_hand((True, True, False, False), thumb="out")),
            template["template"],
            template["threshold"],
        )
        self.assertGreater(score, 0.5)
        self.assertGreater(template["threshold"], 0.0)

    def test_template_rejects_other_gesture(self):
        samples = [to_pixels(make_hand((True, True, False, False))) for _ in range(10)]
        template = build_template(samples)
        score = match_score(
            to_pixels(make_hand((False, False, False, False))),
            template["template"],
            template["threshold"],
        )
        self.assertLess(score, 0.0)

    def test_best_match_ignores_disabled(self):
        samples = [to_pixels(make_hand((True, True, True, False))) for _ in range(8)]
        template = build_template(samples)
        gestures = [
            {
                "id": "cg_test",
                "enabled": False,
                "template": template["template"],
                "threshold": template["threshold"],
            }
        ]
        probe = to_pixels(make_hand((True, True, True, False)))
        self.assertIsNone(best_custom_match(probe, gestures))
        gestures[0]["enabled"] = True
        result = best_custom_match(probe, gestures)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "cg_test")

    def test_noise_tolerance(self):
        samples = [
            to_pixels(add_noise(make_hand((True, False, False, False)), seed=i))
            for i in range(12)
        ]
        template = build_template(samples)
        score = match_score(
            to_pixels(add_noise(make_hand((True, False, False, False)), seed=99)),
            template["template"],
            template["threshold"],
        )
        self.assertGreater(score, 0.0)

    def test_resolution_scaling_invariance(self):
        """Смена разрешения камеры не должна ломать записанные жесты."""
        samples = [to_pixels(make_hand((True, False, False, False))) for _ in range(10)]
        template = build_template(samples)
        half = to_pixels(make_hand((True, False, False, False)), 320, 240)
        score = match_score(half, template["template"], template["threshold"])
        self.assertGreater(score, 0.0)


class ConfigTests(unittest.TestCase):
    def test_default_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            cfg = default_config()
            cfg["engine"]["hold_ms"] = 333
            save_config(cfg, path)
            loaded = load_config(path)
            self.assertEqual(loaded["engine"]["hold_ms"], 333)
            self.assertIn("bindings", loaded)
            self.assertEqual(len(loaded["bindings"]), len(BUILTIN_GESTURES))
            for meta in BUILTIN_GESTURES:
                self.assertIn(meta["id"], loaded["bindings"])

    def test_old_config_enables_two_hands(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            cfg = default_config()
            cfg["version"] = 1
            cfg["tracking"]["max_hands"] = 1
            save_config(cfg, path)
            loaded = load_config(path)
            self.assertEqual(loaded["tracking"]["max_hands"], 2)
            self.assertEqual(loaded["version"], 2)

    def test_broken_config_is_recovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("{не json", encoding="utf-8")
            cfg = load_config(path)
            self.assertEqual(cfg["version"], 2)
            self.assertTrue(path.exists())

    def test_missing_bindings_are_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"bindings": {"point": {"enabled": False}}}), encoding="utf-8")
            cfg = load_config(path)
            self.assertFalse(cfg["bindings"]["point"]["enabled"])
            self.assertIn("pinch", cfg["bindings"])


class PairGestureTests(unittest.TestCase):
    """Жесты двумя руками: признаки, комбинации, свои шаблоны."""

    @staticmethod
    def hand(
        fingers: tuple[bool, bool, bool, bool] = (True, True, True, True),
        thumb: str = "out",
        offset: tuple[float, float] = (0.0, 0.0),
        scale: float = 1.0,
    ) -> Hand:
        points = to_pixels(make_hand(fingers, thumb=thumb, offset=offset, scale=scale))
        return Hand(points=points, width=640, height=480)

    def test_classify_pair(self):
        self.assertEqual(classify_pair("open_palm", "open_palm"), "two_open_palms")
        self.assertEqual(classify_pair("fist", "fist"), "two_fists")
        self.assertEqual(classify_pair("pinch", "pinch"), "two_pinches")
        self.assertEqual(classify_pair("fist", "open_palm") is None, True)
        self.assertIsNone(classify_pair(None, "fist"))

    def test_pair_vector_is_order_independent(self):
        left = self.hand(offset=(0.0, 0.0))
        right = self.hand(offset=(0.25, 0.02))
        forward = pair_feature_vector([left, right])
        backward = pair_feature_vector([right, left])
        self.assertLess(float(np.linalg.norm(forward - backward)), 1e-4)

    def test_pair_vector_translation_and_scale_invariance(self):
        left = self.hand(offset=(0.0, 0.0))
        right = self.hand(offset=(0.25, 0.02))
        base = pair_feature_vector([left, right])

        moved = pair_feature_vector(
            [self.transform(left, 1.25, (0.1, -0.08)), self.transform(right, 1.25, (0.1, -0.08))]
        )
        self.assertLess(float(np.linalg.norm(base - moved)), 0.02)

    @staticmethod
    def transform(hand: Hand, scale: float, shift: tuple[float, float]) -> Hand:
        """Одна и та же аффинная трансформация для обеих рук."""
        points = hand.points.astype(np.float32).copy()
        center = np.array([320.0, 240.0, 0.0], dtype=np.float32)
        delta = np.array([shift[0] * 640, shift[1] * 480, 0.0], dtype=np.float32)
        points = (points - center) * scale + center + delta
        return Hand(points=points, width=640, height=480)

    def test_pair_vector_depends_on_hand_distance(self):
        close = pair_feature_vector([self.hand(offset=(0.0, 0.0)), self.hand(offset=(0.15, 0.0))])
        far = pair_feature_vector([self.hand(offset=(0.0, 0.0)), self.hand(offset=(0.35, 0.0))])
        self.assertGreater(float(np.linalg.norm(close - far)), 0.05)

    def test_pair_template_matches_and_rejects_one_hand(self):
        left = self.hand(fingers=(False, False, False, False), thumb="up")
        right = self.hand(fingers=(False, False, False, False), thumb="up", offset=(0.25, 0.0))
        samples = [[left, right] for _ in range(8)]
        template = build_pair_template(samples)
        score = match_pair_score([left, right], template["template"], template["threshold"])
        self.assertGreater(score, 0.9)
        self.assertLess(
            match_pair_score([left], template["template"], template["threshold"]), 0.0
        )

    def test_best_pair_match_requires_two_hands(self):
        left = self.hand(fingers=(False, False, False, False), thumb="up")
        right = self.hand(fingers=(False, False, False, False), thumb="up", offset=(0.25, 0.0))
        template = build_pair_template([[left, right] for _ in range(8)])
        gestures = [
            {
                "id": "cg_pair",
                "enabled": True,
                "hands": 2,
                "template": template["template"],
                "threshold": template["threshold"],
            }
        ]
        self.assertIsNone(best_pair_match([left], gestures))
        result = best_pair_match([left, right], gestures)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "cg_pair")

    def test_single_hand_match_ignores_pair_template(self):
        left = self.hand()
        right = self.hand(offset=(0.25, 0.0))
        template = build_pair_template([[left, right] for _ in range(8)])
        gestures = [
            {
                "id": "cg_pair",
                "enabled": True,
                "hands": 2,
                "template": template["template"],
                "threshold": template["threshold"],
            }
        ]
        self.assertIsNone(best_custom_match(to_pixels(make_hand()), gestures))


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.cfg = default_config()
        self.cfg["engine"]["hold_ms"] = 150
        self.cfg["engine"]["stabilize_frames"] = 3
        self.cfg["engine"]["cooldown_ms"] = 100
        self.events = []
        self.fired = []
        self.moved = []

        self._orig_execute = engine_module.execute
        self._orig_move = engine_module.set_cursor_pos
        self._orig_screen = engine_module.screen_rect

        engine_module.execute = lambda system, action: self.fired.append(action) or None
        engine_module.set_cursor_pos = lambda x, y: self.moved.append((x, y))
        engine_module.screen_rect = lambda: (0, 0, 1920, 1080)

        self.engine = GestureEngine(self.cfg, self.events.append)
        self.clock = 0.0

    def tearDown(self):
        engine_module.execute = self._orig_execute
        engine_module.set_cursor_pos = self._orig_move
        engine_module.screen_rect = self._orig_screen

    def hand(self, points: np.ndarray) -> Hand:
        return Hand(points=points * np.array([640, 480, 640], dtype=np.float32), width=640, height=480)

    def feed(self, points: np.ndarray, frames: int = 12) -> None:
        for _ in range(frames):
            self.clock += 0.03
            self.engine.process(self.hand(points), self.clock)

    def test_discrete_action_fires_once(self):
        self.cfg["bindings"]["fist"]["action"] = {"type": "hotkey", "params": {"keys": "alt+f4"}}
        self.feed(make_hand((False, False, False, False)), 20)
        actions = [e for e in self.events if e.kind == "action"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(len(self.fired), 1)

    def test_point_moves_cursor(self):
        for i in range(12):
            self.clock += 0.03
            points = make_hand((True, False, False, False), offset=(i * 0.01, 0.0))
            self.engine.process(self.hand(points), self.clock)
        self.assertGreater(len(self.moved), 3)

    def pair(self, pose_a: np.ndarray, pose_b: np.ndarray) -> list:
        return [self.hand(pose_a), self.hand(pose_b)]

    def feed_pair(self, pose_a: np.ndarray, pose_b: np.ndarray, frames: int = 25) -> None:
        hands = self.pair(pose_a, pose_b)
        for _ in range(frames):
            self.clock += 0.03
            self.engine.process(hands, self.clock)

    def test_two_open_palms_fire_pair_action_once(self):
        pose = make_hand((True, True, True, True), thumb="out")
        other = make_hand((True, True, True, True), thumb="out", offset=(0.25, 0.02))
        self.feed_pair(pose, other)
        actions = [e for e in self.events if e.kind == "action"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].gesture, "two_open_palms")
        self.assertEqual(self.fired[0]["type"], "window")
        self.assertEqual(self.engine.last_state.hands, 2)
        self.assertTrue(self.engine.last_state.pair)

    def test_two_hands_do_not_scroll_single_hand_action(self):
        pose = make_hand((True, True, True, True), thumb="out")
        other = make_hand((True, True, True, True), thumb="out", offset=(0.25, 0.02))
        scrolled = []
        original = self.engine.system.scroll
        self.engine.system.scroll = lambda steps, horizontal=False: scrolled.append(steps)
        try:
            self.feed_pair(pose, other)
        finally:
            self.engine.system.scroll = original
        self.assertEqual(scrolled, [])

    def test_single_hand_works_while_other_hand_is_visible(self):
        fist = make_hand((False, False, False, False), offset=(0.32, 0.02), thumb="up")
        for i in range(14):
            self.clock += 0.03
            point = make_hand((True, False, False, False), offset=(i * 0.012, 0.0))
            self.engine.process([self.hand(point), self.hand(fist)], self.clock)
        self.assertGreater(len(self.moved), 3)
        self.assertEqual(self.engine.last_state.hands, 2)
        self.assertFalse(self.engine.last_state.pair)

    def test_custom_pair_gesture_wins(self):
        pose = make_hand((False, False, False, False), thumb="up")
        other = make_hand(
            (False, False, False, False), thumb="up", offset=(0.25, 0.0)
        )
        samples = [[self.hand(pose), self.hand(other)] for _ in range(8)]
        template = build_pair_template(samples)
        self.cfg["custom_gestures"] = [
            {
                "id": "cg_two_thumbs",
                "name": "Два больших пальца",
                "enabled": True,
                "hands": 2,
                "template": template["template"],
                "threshold": template["threshold"],
                "action": {"type": "launch", "params": {"target": "notepad.exe"}},
            }
        ]
        self.feed_pair(pose, other)
        actions = [e for e in self.events if e.kind == "action"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].gesture, "cg_two_thumbs")
        self.assertEqual(self.fired[0]["type"], "launch")

    def test_paused_engine_does_nothing(self):
        self.cfg["bindings"]["fist"]["action"] = {"type": "hotkey", "params": {"keys": "alt+f4"}}
        self.engine.set_paused(True)
        self.feed(make_hand((False, False, False, False)), 20)
        self.assertEqual(self.fired, [])
        self.assertEqual(self.moved, [])
        self.assertTrue(self.engine.last_state.paused)

    def test_suspended_engine_does_nothing(self):
        self.engine.set_suspended(True)
        self.feed(make_hand((True, False, False, False)), 10)
        self.assertEqual(self.moved, [])

    def test_no_hand_resets(self):
        self.feed(make_hand((False, False, False, False)), 10)
        self.clock += 0.03
        state = self.engine.process(None, self.clock)
        self.assertFalse(state.hand)
        self.assertIsNone(state.active)

    def test_custom_gesture_wins(self):
        samples = [
            to_pixels(make_hand((True, False, False, True), thumb="out")) for _ in range(10)
        ]
        template = build_template(samples)
        self.cfg["custom_gestures"] = [
            {
                "id": "cg_rock",
                "name": "Рок",
                "enabled": True,
                "template": template["template"],
                "threshold": template["threshold"],
                "action": {"type": "launch", "params": {"target": "notepad.exe"}},
            }
        ]
        self.feed(make_hand((True, False, False, True), thumb="out"), 20)
        actions = [e for e in self.events if e.kind == "action"]
        self.assertTrue(actions)
        self.assertEqual(self.fired[0]["type"], "launch")


class HotkeyTest(unittest.TestCase):
    def test_parse_modifiers_and_letter(self):
        self.assertEqual(
            parse_combo("ctrl+alt+q"), (MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, 0x51)
        )
        self.assertEqual(
            parse_combo("Ctrl+Shift+F9"), (MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x78)
        )
        self.assertEqual(parse_combo("win+d"), (MOD_WIN | MOD_NOREPEAT, 0x44))

    def test_parse_named_keys(self):
        self.assertEqual(parse_combo("alt+space"), (MOD_ALT | MOD_NOREPEAT, 0x20))
        self.assertEqual(parse_combo("ctrl+pageup")[1], 0x21)
        self.assertEqual(parse_combo("ctrl+esc")[1], 0x1B)

    def test_parse_rejects_invalid(self):
        self.assertIsNone(parse_combo(""))
        self.assertIsNone(parse_combo("ctrl"))
        self.assertIsNone(parse_combo("ctrl+shift"))
        self.assertIsNone(parse_combo("ctrl+нечто"))
        self.assertIsNone(parse_combo("+"))

    def test_parse_ignores_extra_spaces_and_case(self):
        self.assertEqual(parse_combo("  CTRL + Alt + Q "), parse_combo("ctrl+alt+q"))

    def test_pretty(self):
        self.assertEqual(pretty_combo("ctrl+alt+q"), "Ctrl+Alt+Q")
        self.assertEqual(pretty_combo("win+shift+f12"), "Win+Shift+F12")

    def test_register_without_qt_returns_result(self):
        if sys.platform != "win32":
            self.skipTest("только Windows")
        hotkey = GlobalHotkey()
        try:
            ok, error = hotkey.register("ctrl+alt+q")
            self.assertIsInstance(ok, bool)
            self.assertIsInstance(error, str)
        finally:
            hotkey.unregister()
        self.assertEqual(hotkey.backend, "none")


class CameraHelperTest(unittest.TestCase):
    DEVICES = [
        CameraDevice(index=0, name="Integrated Camera"),
        CameraDevice(index=1, name="OBS Virtual Camera"),
    ]

    def test_resolve_by_name(self):
        with mock.patch(
            "app.core.cameras.list_cameras", return_value=self.DEVICES
        ):
            self.assertEqual(resolve_index("OBS Virtual Camera", 0), 1)
            self.assertEqual(resolve_index("obs virtual camera", 0), 1)

    def test_resolve_falls_back_to_index(self):
        with mock.patch(
            "app.core.cameras.list_cameras", return_value=self.DEVICES
        ):
            self.assertEqual(resolve_index("Camera that is gone", 2), 2)
            self.assertEqual(resolve_index("", 3), 3)
            self.assertEqual(resolve_index("   ", 4), 4)

    def test_negative_fallback_is_zero(self):
        with mock.patch("app.core.cameras.list_cameras", return_value=[]):
            self.assertEqual(resolve_index("", -5), 0)


if __name__ == "__main__":
    unittest.main()

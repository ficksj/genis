"""Движок: превращает поток рук в события жестов и действия системы."""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from .actions import describe, execute, is_continuous
from .builtin import classify, classify_pair
from .custom import best_custom_match, best_pair_match
from .features import INDEX_TIP, Hand
from .smoothing import OneEuroFilter
from .system_win import SystemController, screen_rect, set_cursor_pos

CustomPriority = 0.55


@dataclass
class EngineState:
    hand: bool = False
    hands: int = 0
    gesture: str | None = None
    secondary: str | None = None
    confidence: float = 0.0
    source: str = ""
    stable: bool = False
    active: str | None = None
    action: str = ""
    paused: bool = False
    pair: bool = False
    cursor: tuple[int, int] | None = None


@dataclass
class EngineEvent:
    kind: str                      # action | drag | state | error
    gesture: str = ""
    text: str = ""
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class GestureEngine:
    def __init__(self, cfg: dict[str, Any], on_event: Callable[[EngineEvent], None] | None = None):
        self.cfg = cfg
        self.on_event = on_event or (lambda event: None)
        self.system = SystemController()
        self.paused = bool(cfg.get("app", {}).get("start_paused", False))
        self.suspended = False

        self._history: deque[str] = deque(maxlen=16)
        self._candidate: str | None = None
        self._candidate_since: float = 0.0
        self._active: str | None = None
        self._active_since: float = 0.0
        self._mismatch = 0

        # Отдельное состояние для жестов двумя руками: они приоритетнее
        # одиночных и не должны смешиваться с их стабилизацией.
        self._pair_history: deque[str] = deque(maxlen=16)
        self._pair_candidate: str | None = None
        self._pair_since: float = 0.0
        self._pair_active: str | None = None
        self._pair_active_since: float = 0.0
        self._pair_mismatch = 0

        self._last_fire: dict[str, float] = {}
        self._last_repeat: dict[str, float] = {}

        self._drag = False
        self._drag_button = "left"

        self._fx = OneEuroFilter(mincutoff=1.4, beta=0.6)
        self._fy = OneEuroFilter(mincutoff=1.4, beta=0.6)
        self._cursor_norm: tuple[float, float] | None = None
        self._cursor_px: tuple[int, int] | None = None
        self._last_cursor_t = 0.0

        self._scroll_prev: float | None = None
        self._scroll_acc = 0.0

        self._screen = screen_rect()
        self._screen_t = 0.0
        self.last_state = EngineState(paused=self.paused)

    # --- публичное API ---------------------------------------------------
    def set_paused(self, paused: bool, now: float | None = None) -> None:
        self.paused = bool(paused)
        if self.paused:
            moment = now or time.perf_counter()
            self._deactivate(moment, lost=True)
            self._deactivate_pair(moment, lost=True)
            self._reset_stability()
        self.last_state.paused = self.paused
        self.on_event(EngineEvent(kind="state", text="paused" if self.paused else "running"))

    def set_suspended(self, suspended: bool) -> None:
        """Временно отключает действия (например, на время записи жеста)."""
        self.suspended = bool(suspended)
        if self.suspended:
            moment = time.perf_counter()
            self._deactivate(moment, lost=True)
            self._deactivate_pair(moment, lost=True)
            self._reset_stability()

    def reload(self) -> None:
        """Сбрасывает внутреннее состояние после изменения настроек."""
        self._fx.reset()
        self._fy.reset()
        self._cursor_norm = None
        self._cursor_px = None
        self._scroll_prev = None
        self._scroll_acc = 0.0
        self._deactivate_pair(time.perf_counter(), lost=True)
        self._reset_stability()

    def _reset_stability(self) -> None:
        self._candidate = None
        self._history.clear()
        self._mismatch = 0
        self._pair_candidate = None
        self._pair_history.clear()
        self._pair_mismatch = 0

    @staticmethod
    def _normalize_hands(hand: Hand | list[Hand] | tuple[Hand, ...] | None) -> list[Hand]:
        if hand is None:
            return []
        if isinstance(hand, Hand):
            return [hand]
        return [item for item in hand if item is not None]

    def process(
        self,
        hand: Hand | list[Hand] | tuple[Hand, ...] | None,
        now: float | None = None,
    ) -> EngineState:
        now = now or time.perf_counter()
        hands = self._normalize_hands(hand)
        state = EngineState(hand=bool(hands), hands=len(hands), paused=self.paused)

        if not hands or self.paused:
            self._deactivate(now, lost=True)
            self._deactivate_pair(now, lost=True)
            self._reset_stability()
            self.last_state = state
            return state

        primary = hands[0]
        gesture, confidence, source = self._detect(primary)
        state.gesture = gesture
        state.confidence = confidence
        state.source = source

        secondary_gesture: str | None = None
        if len(hands) >= 2:
            secondary_gesture, _secondary_conf = classify(hands[1].points)
        state.secondary = secondary_gesture

        pair = self._detect_pair(hands) if len(hands) >= 2 else None

        if self.suspended:
            self._deactivate(now, lost=True)
            self._deactivate_pair(now, lost=True)
            self._reset_stability()
            if pair is not None:
                state.gesture, state.confidence, state.source = pair
                state.pair = True
            self.last_state = state
            return state

        if pair is not None:
            # Двурукий жест приоритетнее одиночных: пока он держится, действия
            # одной рукой не выполняются, чтобы не было кликов и прокрутки.
            self._deactivate(now, lost=True)
            self._candidate = None
            self._history.clear()
            self._mismatch = 0
            pair_id, pair_conf, pair_source = pair
            state.gesture = pair_id
            state.confidence = pair_conf
            state.source = pair_source
            state.pair = True

            stable, active = self._run_pair(pair_id, now)
            state.stable = stable
            state.active = active
            if active:
                action = self._action_for(active)
                state.action = describe(action)
                self._tick_active(
                    now, action, gesture=active, active_since=self._pair_active_since
                )
            self.last_state = state
            return state

        if self._pair_active is not None:
            self._deactivate_pair(now, lost=True)
        self._pair_history.clear()
        self._pair_candidate = None
        self._pair_mismatch = 0

        # Стабилизация: жест должен держаться несколько кадров и hold_ms.
        if gesture != self._candidate:
            self._candidate = gesture
            self._candidate_since = now
        self._history.append(gesture)

        need = max(2, int(self.cfg["engine"].get("stabilize_frames", 4)))
        recent = list(self._history)[-need:]
        frames_ok = len(recent) >= need and len(set(recent)) == 1
        hold_ok = (now - self._candidate_since) * 1000.0 >= float(
            self.cfg["engine"].get("hold_ms", 220)
        )
        stable = frames_ok and hold_ok
        state.stable = stable

        # Смена жеста: старый деактивируем быстро, чтобы клик не «залипал».
        if self._active is not None and gesture != self._active:
            self._mismatch += 1
            if self._mismatch >= 2 and (now - self._active_since) >= 0.05:
                self._deactivate(now, lost=False)
        else:
            self._mismatch = 0

        if stable and self._active != gesture:
            self._activate(gesture, now)

        active = self._active
        state.active = active
        if active:
            action = self._action_for(active)
            state.action = describe(action)
            self._tick_active(now, action)

        # Непрерывные действия работают сразу, без задержки на стабилизацию.
        if self._cursor_gesture(gesture):
            self._move_cursor(primary, now)
            state.cursor = self._cursor_px
        if active and gesture == active:
            action = self._action_for(active)
            if action.get("type") == "scroll":
                self._scroll(primary)

        self.last_state = state
        return state

    # --- поиск действия --------------------------------------------------
    def _action_for(self, gesture_id: str | None) -> dict[str, Any]:
        if not gesture_id:
            return {"type": "none", "params": {}}
        for custom in self.cfg.get("custom_gestures", []):
            if custom.get("id") == gesture_id:
                if not custom.get("enabled", True):
                    return {"type": "none", "params": {}}
                return custom.get("action") or {"type": "none", "params": {}}
        binding = self.cfg.get("bindings", {}).get(gesture_id) or {}
        if not binding.get("enabled", True):
            return {"type": "none", "params": {}}
        return binding.get("action") or {"type": "none", "params": {}}

    def _detect(self, hand: Hand) -> tuple[str, float, str]:
        gesture, confidence = classify(hand.points)
        best = best_custom_match(hand.points, self.cfg.get("custom_gestures", []))
        if best is not None:
            custom_id, score = best
            if score >= CustomPriority:
                return custom_id, min(1.0, max(0.0, score)), "custom"
        return gesture, confidence, "builtin"

    def _detect_pair(self, hands: list[Hand]) -> tuple[str, float, str] | None:
        """Жест двумя руками: свой шаблон или известная комбинация."""
        best = best_pair_match(hands[:2], self.cfg.get("custom_gestures", []))
        if best is not None:
            custom_id, score = best
            if score >= CustomPriority:
                return custom_id, min(1.0, max(0.0, score)), "custom"

        first, conf_a = classify(hands[0].points)
        second, conf_b = classify(hands[1].points)
        pair_id = classify_pair(first, second)
        if pair_id is None:
            return None
        binding = self.cfg.get("bindings", {}).get(pair_id) or {}
        if not binding.get("enabled", True):
            return None
        return pair_id, min(conf_a, conf_b), "builtin"

    # --- стабилизация двух рук ------------------------------------------
    def _run_pair(self, gesture: str, now: float) -> tuple[bool, str | None]:
        if gesture != self._pair_candidate:
            self._pair_candidate = gesture
            self._pair_since = now
        self._pair_history.append(gesture)

        need = max(2, int(self.cfg["engine"].get("stabilize_frames", 4)))
        recent = list(self._pair_history)[-need:]
        frames_ok = len(recent) >= need and len(set(recent)) == 1
        hold_ms = float(
            self.cfg["engine"].get(
                "pair_hold_ms", self.cfg["engine"].get("hold_ms", 180)
            )
            or 0
        )
        hold_ok = (now - self._pair_since) * 1000.0 >= hold_ms
        stable = frames_ok and hold_ok

        if self._pair_active is not None and gesture != self._pair_active:
            self._pair_mismatch += 1
            if self._pair_mismatch >= 2 and (now - self._pair_active_since) >= 0.05:
                self._deactivate_pair(now, lost=False)
        else:
            self._pair_mismatch = 0

        if stable and self._pair_active != gesture:
            self._activate_pair(gesture, now)
        return stable, self._pair_active

    def _activate_pair(self, gesture: str, now: float) -> None:
        self._pair_active = gesture
        self._pair_active_since = now
        self._pair_mismatch = 0
        action = self._action_for(gesture)
        if action.get("type") == "none" or is_continuous(action):
            return
        self._fire(gesture, action, now)

    def _deactivate_pair(self, now: float, lost: bool = True) -> None:
        # У двуруких жестов нет удержаний вроде drag — достаточно сбросить состояние.
        self._pair_active = None
        self._pair_active_since = 0.0
        self._pair_mismatch = 0

    # --- активация -------------------------------------------------------
    def _activate(self, gesture: str, now: float) -> None:
        self._active = gesture
        self._active_since = now
        self._mismatch = 0
        action = self._action_for(gesture)

        if action.get("type") == "none" or is_continuous(action):
            return

        if self._is_drag_action(action) and gesture == "pinch":
            self._drag = False
            self._drag_button = action.get("params", {}).get("button", "left")
            return

        self._fire(gesture, action, now)

    def _deactivate(self, now: float, lost: bool) -> None:
        if self._active is None:
            return
        gesture = self._active
        action = self._action_for(gesture)

        if self._is_drag_action(action) and gesture == "pinch":
            if self._drag:
                self.system.mouse_up(self._drag_button)
                self._drag = False
                self.on_event(
                    EngineEvent(kind="drag", gesture=gesture, text="Перетаскивание завершено")
                )
            elif not lost:
                self._click_pinch(now)

        self._active = None
        self._active_since = 0.0
        self._mismatch = 0

    def _click_pinch(self, now: float) -> None:
        action = self._action_for("pinch")
        # Для щипка пауза короче, иначе не получится быстро кликать дважды.
        cooldown = min(0.25, float(self.cfg["engine"].get("cooldown_ms", 500)) / 1000.0)
        if now - self._last_fire.get("pinch", 0.0) < cooldown:
            return
        self._last_fire["pinch"] = now
        button = action.get("params", {}).get("button", "left")
        self.system.click(button)
        self.on_event(
            EngineEvent(kind="action", gesture="pinch", text=describe(action))
        )

    def _tick_active(
        self,
        now: float,
        action: dict[str, Any],
        gesture: str | None = None,
        active_since: float | None = None,
    ) -> None:
        gesture = gesture or self._active
        if gesture is None:
            return
        since = self._active_since if active_since is None else active_since

        if self._is_drag_action(action) and gesture == "pinch":
            drag_after = float(self.cfg["engine"].get("drag_ms", 350)) / 1000.0
            if not self._drag and (now - since) >= drag_after:
                self._drag_button = action.get("params", {}).get("button", "left")
                self.system.mouse_down(self._drag_button)
                self._drag = True
                self.on_event(
                    EngineEvent(kind="drag", gesture=gesture, text="Перетаскивание…")
                )
            return

        if action.get("type") in ("media", "brightness"):
            repeat = float(self.cfg["engine"].get("repeat_ms", 550)) / 1000.0
            if repeat <= 0:
                return
            if (now - since) >= repeat:
                last = self._last_repeat.get(gesture, 0.0)
                if now - last >= repeat:
                    self._last_repeat[gesture] = now
                    self._fire(gesture, action, now, ignore_cooldown=True)

    def _fire(
        self,
        gesture: str,
        action: dict[str, Any],
        now: float,
        ignore_cooldown: bool = False,
    ) -> None:
        cooldown = float(self.cfg["engine"].get("cooldown_ms", 700)) / 1000.0
        if not ignore_cooldown and now - self._last_fire.get(gesture, 0.0) < cooldown:
            return
        self._last_fire[gesture] = now
        error = execute(self.system, action)
        self.on_event(
            EngineEvent(
                kind="action",
                gesture=gesture,
                text=describe(action),
                error=error,
            )
        )

    def _is_drag_action(self, action: dict[str, Any]) -> bool:
        return (
            action.get("type") == "mouse"
            and action.get("params", {}).get("action") == "click"
            and bool(action.get("params", {}).get("drag", False))
        )

    # --- курсор / прокрутка ---------------------------------------------
    def _cursor_gesture(self, gesture: str) -> bool:
        action = self._action_for(gesture)
        if action.get("type") == "cursor_move":
            return True
        if gesture == "pinch" and self._is_drag_action(action):
            return self._action_for("point").get("type") == "cursor_move"
        return False

    def _move_cursor(self, hand: Hand, now: float) -> None:
        cursor_cfg = self.cfg["engine"]["cursor"]
        if not cursor_cfg.get("enabled", True):
            return

        tip = hand.points[INDEX_TIP]
        nx = float(tip[0]) / max(1, hand.width)
        ny = float(tip[1]) / max(1, hand.height)

        margin = max(0.0, min(0.35, float(cursor_cfg.get("margin", 0.10))))
        span = max(0.05, 1.0 - 2.0 * margin)
        nx = (nx - margin) / span
        ny = (ny - margin) / span

        sensitivity = float(cursor_cfg.get("sensitivity", 1.0))
        nx = 0.5 + (nx - 0.5) * sensitivity
        ny = 0.5 + (ny - 0.5) * sensitivity
        nx = max(0.0, min(1.0, nx))
        ny = max(0.0, min(1.0, ny))

        dt = now - self._last_cursor_t
        if dt <= 1e-4:
            dt = 1.0 / 30.0
        self._last_cursor_t = now

        smoothing = max(0.0, min(0.95, float(cursor_cfg.get("smoothing", 0.55))))
        cutoff = 6.0 * (1.0 - smoothing) ** 2 + 0.25
        self._fx.mincutoff = cutoff
        self._fy.mincutoff = cutoff

        if self._cursor_norm is not None:
            jump = math.hypot(nx - self._cursor_norm[0], ny - self._cursor_norm[1])
            if jump > 0.35:
                self._fx.reset()
                self._fy.reset()

        # Раз в 5 секунд перечитываем геометрию: пользователь мог подключить
        # второй монитор или поменять масштаб.
        if now - self._screen_t > 5.0:
            self._screen = screen_rect()
            self._screen_t = now

        sx = self._fx(nx, dt)
        sy = self._fy(ny, dt)
        self._cursor_norm = (nx, ny)

        px = self._screen[0] + int(round(sx * self._screen[2]))
        py = self._screen[1] + int(round(sy * self._screen[3]))
        dead = float(cursor_cfg.get("dead_zone", 2))
        if self._cursor_px is None or math.hypot(
            px - self._cursor_px[0], py - self._cursor_px[1]
        ) >= dead:
            set_cursor_pos(px, py)
            self._cursor_px = (px, py)

    def _scroll(self, hand: Hand) -> None:
        scroll_cfg = self.cfg["engine"]["scroll"]
        center_y = float(hand.center[1]) / max(1, hand.height)

        if self._scroll_prev is None or abs(center_y - self._scroll_prev) > 0.18:
            self._scroll_prev = center_y
            self._scroll_acc = 0.0
            return

        dy = center_y - self._scroll_prev
        self._scroll_prev = center_y
        if scroll_cfg.get("invert", False):
            dy = -dy

        self._scroll_acc += -dy * 30.0 * float(scroll_cfg.get("speed", 1.0))
        steps = int(self._scroll_acc)
        if steps:
            steps = max(-4, min(4, steps))
            self.system.scroll(steps)
            self._scroll_acc -= steps

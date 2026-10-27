"""Конфигурация приложения: значения по умолчанию, загрузка и сохранение."""

from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import config_path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str = "cg") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# --- Библиотека встроенных жестов -----------------------------------------
# kind: continuous — обрабатывается каждый кадр (курсор/скролл),
#       discrete   — срабатывает один раз при появлении жеста.
BUILTIN_GESTURES: list[dict[str, Any]] = [
    {
        "id": "point",
        "name": "Указательный палец",
        "hint": "Только указательный вытянут — курсор следует за кончиком пальца",
        "kind": "continuous",
    },
    {
        "id": "pinch",
        "name": "Щипок",
        "hint": "Большой и указательный соединены — клик, удержание = перетаскивание",
        "kind": "discrete",
    },
    {
        "id": "peace",
        "name": "Два пальца",
        "hint": "Указательный и средний — правый клик",
        "kind": "discrete",
    },
    {
        "id": "three",
        "name": "Три пальца",
        "hint": "Указательный, средний, безымянный — переключение окон (Alt+Tab)",
        "kind": "discrete",
    },
    {
        "id": "four",
        "name": "Четыре пальца",
        "hint": "Все пальцы кроме большого — свернуть все окна (Win+D)",
        "kind": "discrete",
    },
    {
        "id": "open_palm",
        "name": "Открытая ладонь",
        "hint": "Все пять пальцев — прокрутка движением руки вверх/вниз",
        "kind": "continuous",
    },
    {
        "id": "fist",
        "name": "Кулак",
        "hint": "Пальцы сжаты — нейтральное положение (по умолчанию ничего не делает)",
        "kind": "discrete",
    },
    {
        "id": "thumbs_up",
        "name": "Большой палец вверх",
        "hint": "Кулак с поднятым большим пальцем — громкость больше",
        "kind": "discrete",
    },
    {
        "id": "thumbs_down",
        "name": "Большой палец вниз",
        "hint": "Кулак с опущенным большим пальцем — громкость меньше",
        "kind": "discrete",
    },
    {
        "id": "rock",
        "name": "Рок",
        "hint": "Указательный и мизинец вверх — play/pause в плеере",
        "kind": "discrete",
    },
    {
        "id": "ok",
        "name": "ОК",
        "hint": "Щипок, остальные три пальца вытянуты — проводник (Win+E)",
        "kind": "discrete",
    },
    {
        "id": "two_open_palms",
        "name": "Две ладони",
        "hint": "Обе руки открыты ладонями — все окна (Win+Tab)",
        "kind": "discrete",
        "pair": True,
    },
    {
        "id": "two_fists",
        "name": "Два кулака",
        "hint": "Обе руки сжаты в кулаки — play/pause в плеере",
        "kind": "discrete",
        "pair": True,
    },
    {
        "id": "two_pinches",
        "name": "Двойной щипок",
        "hint": "Щипок обеими руками одновременно — правый клик",
        "kind": "discrete",
        "pair": True,
    },
]

BUILTIN_BY_ID = {g["id"]: g for g in BUILTIN_GESTURES}


def default_action(kind: str) -> dict[str, Any]:
    """Действие по умолчанию для типа."""
    return {"type": kind, "params": {}}


DEFAULT_BINDINGS: dict[str, dict[str, Any]] = {
    "point": {
        "enabled": True,
        "action": {"type": "cursor_move", "params": {}},
    },
    "pinch": {
        "enabled": True,
        "action": {
            "type": "mouse",
            "params": {"button": "left", "action": "click", "drag": True},
        },
    },
    "peace": {
        "enabled": True,
        "action": {"type": "mouse", "params": {"button": "right", "action": "click", "drag": False}},
    },
    "three": {
        "enabled": True,
        "action": {"type": "window", "params": {"command": "alt_tab"}},
    },
    "four": {
        "enabled": True,
        "action": {"type": "window", "params": {"command": "show_desktop"}},
    },
    "open_palm": {
        "enabled": True,
        "action": {"type": "scroll", "params": {}},
    },
    "fist": {"enabled": True, "action": {"type": "none", "params": {}}},
    "thumbs_up": {
        "enabled": True,
        "action": {"type": "media", "params": {"key": "volume_up"}},
    },
    "thumbs_down": {
        "enabled": True,
        "action": {"type": "media", "params": {"key": "volume_down"}},
    },
    "rock": {
        "enabled": True,
        "action": {"type": "media", "params": {"key": "play_pause"}},
    },
    "ok": {
        "enabled": True,
        "action": {"type": "window", "params": {"command": "explorer"}},
    },
    "two_open_palms": {
        "enabled": True,
        "action": {"type": "window", "params": {"command": "task_view"}},
    },
    "two_fists": {
        "enabled": True,
        "action": {"type": "media", "params": {"key": "play_pause"}},
    },
    "two_pinches": {
        "enabled": True,
        "action": {
            "type": "mouse",
            "params": {"button": "right", "action": "click", "drag": False},
        },
    },
}


def default_config() -> dict[str, Any]:
    return {
        "version": 2,
        "camera": {
            "index": 0,
            "device_name": "",
            "width": 640,
            "height": 480,
            "fps": 30,
            "mirror": True,
            "show_landmarks": True,
        },
        "tracking": {
            "max_hands": 2,
            "min_detection": 0.6,
            "min_presence": 0.5,
            "min_tracking": 0.5,
        },
        "engine": {
            "stabilize_frames": 4,
            "hold_ms": 180,
            "pair_hold_ms": 350,
            "cooldown_ms": 500,
            "repeat_ms": 550,
            "drag_ms": 550,
            "cursor": {
                "enabled": True,
                "sensitivity": 1.0,
                "smoothing": 0.55,
                "margin": 0.10,
                "dead_zone": 2,
            },
            "scroll": {"speed": 1.0, "invert": False},
            "pause_hotkey": "ctrl+alt+q",
            "sounds": False,
        },
        "bindings": copy.deepcopy(DEFAULT_BINDINGS),
        "custom_gestures": [],
        "library": [
            {"id": "lib_steam", "name": "Steam", "target": "steam://open/main"},
            {"id": "lib_notepad", "name": "Блокнот", "target": "notepad.exe"},
        ],
        "app": {
            "first_run": True,
            "autostart": False,
            "start_paused": False,
            "minimize_to_tray": True,
            "show_window_on_start": True,
        },
    }


def _deep_merge(base: dict, override: dict) -> dict:
    """Дополняет base значениями из override (dict —рекурсивно)."""
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _migrate(cfg: dict[str, Any]) -> dict[str, Any]:
    # Добавляем новые встроенные жесты, если их ещё нет в конфиге.
    bindings = cfg.setdefault("bindings", {})
    for gesture_id, binding in DEFAULT_BINDINGS.items():
        bindings.setdefault(gesture_id, copy.deepcopy(binding))
    cfg.setdefault("custom_gestures", [])
    cfg.setdefault("library", [])
    cfg.setdefault("app", {})
    cfg["app"].setdefault("first_run", False)

    # 0.2 → 0.3: включаем вторую руку по умолчанию. Если пользователь потом
    # выберет «1», версия уже 2 и настройку больше не трогаем.
    if int(cfg.get("version", 1)) < 2:
        cfg.setdefault("tracking", {})["max_hands"] = 2
        cfg["version"] = 2
    return cfg


def load_config(path: Path | None = None) -> dict[str, Any]:
    path = path or config_path()
    if not path.exists():
        cfg = default_config()
        save_config(cfg, path)
        return cfg
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        backup = path.with_suffix(".broken.json")
        try:
            path.replace(backup)
        except OSError:
            pass
        cfg = default_config()
        save_config(cfg, path)
        return cfg
    return _migrate(_deep_merge(default_config(), raw))


def save_config(cfg: dict[str, Any], path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def get_gesture_meta(gesture_id: str, cfg: dict[str, Any]) -> dict[str, Any]:
    if gesture_id in BUILTIN_BY_ID:
        return BUILTIN_BY_ID[gesture_id]
    for g in cfg.get("custom_gestures", []):
        if g.get("id") == gesture_id:
            return {
                "id": g["id"],
                "name": g.get("name", "Свой жест"),
                "hint": "Свой записанный жест",
                "kind": "discrete",
                "custom": True,
            }
    return {"id": gesture_id, "name": gesture_id, "hint": "", "kind": "discrete"}

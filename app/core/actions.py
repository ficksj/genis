"""Описание типов действий, их выполнение и человекочитаемые названия."""

from __future__ import annotations

from typing import Any

from .system_win import (
    BUTTON_LABELS,
    MEDIA_LABELS,
    WINDOW_LABELS,
    SystemController,
)

ACTION_TYPES: list[tuple[str, str]] = [
    ("none", "Ничего не делать"),
    ("cursor_move", "Движение курсора"),
    ("scroll", "Прокрутка"),
    ("mouse", "Кнопки мыши"),
    ("hotkey", "Горячие клавиши"),
    ("launch", "Запустить программу / сайт"),
    ("media", "Медиа и громкость"),
    ("brightness", "Яркость экрана"),
    ("window", "Окна Windows"),
    ("text", "Ввести текст"),
    ("command", "Команда Windows (для продвинутых)"),
]

ACTION_TYPE_LABELS = dict(ACTION_TYPES)

MOUSE_ACTIONS = [
    ("click", "Клик"),
    ("double", "Двойной клик"),
    ("down", "Зажать кнопку"),
    ("up", "Отпустить кнопку"),
]

BRIGHTNESS_MODES = [("up", "Увеличить"), ("down", "Уменьшить"), ("set", "Установить")]


def is_continuous(action: dict[str, Any] | None) -> bool:
    return bool(action) and action.get("type") in ("cursor_move", "scroll")


def default_action(kind: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if kind == "mouse":
        params = {"button": "left", "action": "click", "drag": False}
    elif kind == "hotkey":
        params = {"keys": "ctrl+alt+t"}
    elif kind == "media":
        params = {"key": "play_pause"}
    elif kind == "brightness":
        params = {"mode": "up", "step": 10, "value": 50}
    elif kind == "window":
        params = {"command": "show_desktop"}
    elif kind == "launch":
        params = {"target": ""}
    elif kind == "text":
        params = {"text": ""}
    elif kind == "command":
        params = {"command": ""}
    return {"type": kind, "params": params}


def describe(action: dict[str, Any] | None) -> str:
    """Короткое описание действия для интерфейса."""
    if not action:
        return "Ничего"
    kind = action.get("type", "none")
    params = action.get("params") or {}

    if kind == "none":
        return "Ничего"
    if kind == "cursor_move":
        return "Движение курсора"
    if kind == "scroll":
        return "Прокрутка"
    if kind == "mouse":
        name = MOUSE_ACTIONS
        action_name = dict(MOUSE_ACTIONS).get(params.get("action", "click"), "Клик")
        label = f"{action_name}: {BUTTON_LABELS.get(params.get('button', 'left'), 'левая')}"
        if params.get("drag"):
            label += " + перетаскивание"
        return label
    if kind == "hotkey":
        keys = str(params.get("keys", "")).strip()
        return f"Клавиши: {keys.upper()}" if keys else "Клавиши (не заданы)"
    if kind == "media":
        return f"Медиа: {MEDIA_LABELS.get(params.get('key', ''), params.get('key', ''))}"
    if kind == "brightness":
        mode = params.get("mode", "up")
        if mode == "set":
            return f"Яркость: {params.get('value', 50)}%"
        sign = "+" if mode == "up" else "−"
        return f"Яркость: {sign}{params.get('step', 10)}%"
    if kind == "window":
        return WINDOW_LABELS.get(params.get("command", ""), "Окна Windows")
    if kind == "launch":
        target = str(params.get("target", "")).strip()
        if not target:
            return "Запуск (не задано)"
        short = target if len(target) <= 42 else target[:39] + "…"
        return f"Запуск: {short}"
    if kind == "text":
        text = str(params.get("text", ""))
        short = text if len(text) <= 30 else text[:27] + "…"
        return f"Текст: «{short}»" if text else "Текст (пусто)"
    if kind == "command":
        command = str(params.get("command", ""))
        short = command if len(command) <= 38 else command[:35] + "…"
        return f"Команда: {short}" if command else "Команда (пусто)"
    return ACTION_TYPE_LABELS.get(kind, kind)


def execute(system: SystemController, action: dict[str, Any] | None) -> str | None:
    """Выполняет действие. Возвращает текст ошибки или None."""
    if not action:
        return None
    kind = action.get("type", "none")
    params = action.get("params") or {}

    try:
        if kind == "none" or kind in ("cursor_move", "scroll"):
            return None
        if kind == "mouse":
            button = params.get("button", "left")
            name = params.get("action", "click")
            if name == "click":
                system.click(button)
            elif name == "double":
                system.click(button, double=True)
            elif name == "down":
                system.mouse_down(button)
            elif name == "up":
                system.mouse_up(button)
            return None
        if kind == "hotkey":
            system.press_hotkey(str(params.get("keys", "")))
            return None
        if kind == "media":
            system.media(str(params.get("key", "play_pause")))
            return None
        if kind == "brightness":
            mode = params.get("mode", "up")
            if mode == "set":
                return system.set_brightness(int(params.get("value", 50)))
            step = int(params.get("step", 10))
            return system.brightness_step(step if mode == "up" else -step)
        if kind == "window":
            system.window(str(params.get("command", "show_desktop")))
            return None
        if kind == "launch":
            return system.launch(str(params.get("target", "")))
        if kind == "text":
            system.type_text(str(params.get("text", "")))
            return None
        if kind == "command":
            return system.run_command(str(params.get("command", "")))
    except Exception as exc:  # действия не должны ронять трекинг
        return f"Ошибка действия: {exc}"
    return None

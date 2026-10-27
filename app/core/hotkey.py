"""Глобальная горячая клавиша Windows.

Основной путь — Win32 ``RegisterHotKey``: работает, пока приложение свёрнуто,
и не зависит от низкоуровневых хуков. Если комбинацию занять не удалось
(например, её уже слушает другая программа), используется ``pynput``.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
from typing import Callable

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, QTimer, Signal

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

_MODIFIERS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "ctl": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "cmd": MOD_WIN,
    "super": MOD_WIN,
    "meta": MOD_WIN,
}

_NAMED_KEYS = {
    "space": 0x20,
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
    "esc": 0x1B,
    "escape": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "del": 0x2E,
    "insert": 0x2D,
    "ins": 0x2D,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "capslock": 0x14,
    "printscreen": 0x2C,
    "pause": 0x13,
    "numlock": 0x90,
    "scrolllock": 0x91,
    **{f"f{i}": 0x6F + i for i in range(1, 25)},
}

# Клавиши-модификаторы сами по себе не годятся как основная клавиша.
_MODIFIER_VK = {0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5}

_next_hotkey_id = 0


def vk_for_key(token: str) -> int | None:
    """Виртуальный код клавиши по её названию («q», «f5», «space»)."""
    token = (token or "").strip().lower()
    if not token:
        return None
    if token in _NAMED_KEYS:
        return _NAMED_KEYS[token]
    if len(token) == 1 and token.isascii():
        code = ord(token.upper())
        if code < 0x80:
            return code
        return None
    if token.startswith("vk") and token[2:].isdigit():
        return int(token[2:], 10)
    return None


def parse_combo(combo: str) -> tuple[int, int] | None:
    """«Ctrl+Alt+Q» → (MOD_CONTROL|MOD_ALT|MOD_NOREPEAT, VK_Q).

    Возвращает None, если комбинация пустая или в ней нет обычной клавиши.
    """
    parts = [part.strip().lower() for part in (combo or "").split("+") if part.strip()]
    if not parts:
        return None
    modifiers = 0
    key: int | None = None
    for part in parts:
        if part in _MODIFIERS:
            modifiers |= _MODIFIERS[part]
            continue
        code = vk_for_key(part)
        if code is None:
            return None
        key = code
    if key is None or key in _MODIFIER_VK:
        return None
    return modifiers | MOD_NOREPEAT, key


def pretty_combo(combo: str) -> str:
    """Приводит комбинацию к читаемому виду: «ctrl+alt+q» → «Ctrl+Alt+Q»."""
    names = {"ctrl": "Ctrl", "control": "Ctrl", "ctl": "Ctrl", "alt": "Alt", "shift": "Shift",
             "win": "Win", "cmd": "Win", "super": "Win", "meta": "Win"}
    parts = []
    for part in (combo or "").split("+"):
        token = part.strip()
        if not token:
            continue
        lower = token.lower()
        if lower in names:
            parts.append(names[lower])
        elif len(token) == 1:
            parts.append(token.upper())
        elif lower.startswith("f") and lower[1:].isdigit():
            parts.append(lower.upper())
        else:
            parts.append(token[:1].upper() + token[1:])
    return "+".join(parts)


class _NativeFilter(QAbstractNativeEventFilter):
    def __init__(self, owner: "GlobalHotkey") -> None:
        super().__init__()
        self._owner = owner

    def nativeEventFilter(self, eventType, message):  # noqa: N802 - Qt API
        try:
            if bytes(eventType) not in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
                return False, 0
            msg = wt.MSG.from_address(int(message))
        except Exception:
            return False, 0
        if msg.message == WM_HOTKEY and int(msg.wParam) == self._owner.hotkey_id:
            self._owner._fire()
        return False, 0


class GlobalHotkey(QObject):
    """Одна глобальная комбинация с сигналом ``triggered``."""

    triggered = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.hotkey_id = 0
        self.combo = ""
        self.backend = "none"
        self._registered_id = 0
        self._filter: _NativeFilter | None = None
        self._pynput_listener = None

    # --- регистрация ------------------------------------------------------
    def register(self, combo: str) -> tuple[bool, str]:
        """Пытается занять комбинацию. Возвращает (успех, сообщение об ошибке)."""
        self.unregister()
        self.combo = combo
        parsed = parse_combo(combo)
        if parsed is None:
            return False, f"не удалось разобрать комбинацию «{combo}»"
        modifiers, key = parsed

        app = QCoreApplication.instance()
        if app is not None:
            if self._filter is None:
                self._filter = _NativeFilter(self)
                app.installNativeEventFilter(self._filter)
            global _next_hotkey_id
            _next_hotkey_id += 1
            hotkey_id = 0xB000 + (_next_hotkey_id % 0x0FFF)
            user32 = ctypes.windll.user32
            if user32.RegisterHotKey(None, hotkey_id, modifiers, key):
                self.hotkey_id = hotkey_id
                self._registered_id = hotkey_id
                self.backend = "registerhotkey"
                return True, ""

        listener = self._register_pynput(combo)
        if listener is not None:
            self._pynput_listener = listener
            self.backend = "pynput"
            return True, ""
        return False, "комбинация занята другой программой"

    def _register_pynput(self, combo: str):
        try:
            from pynput import keyboard
        except Exception:
            return None
        modifiers = {"ctrl": "<ctrl>", "control": "<ctrl>", "ctl": "<ctrl>",
                     "alt": "<alt>", "shift": "<shift>", "win": "<cmd>",
                     "cmd": "<cmd>", "super": "<cmd>", "meta": "<cmd>"}
        tokens: list[str] = []
        for part in (combo or "").split("+"):
            part = part.strip().lower()
            if not part:
                continue
            tokens.append(modifiers.get(part, part if len(part) == 1 else f"<{part}>"))
        spec = "+".join(tokens)
        try:
            listener = keyboard.GlobalHotKeys({spec: self._fire})
            listener.daemon = True
            listener.start()
            return listener
        except Exception:
            return None

    def unregister(self) -> None:
        if self._pynput_listener is not None:
            try:
                self._pynput_listener.stop()
            except Exception:
                pass
            self._pynput_listener = None
        if self._registered_id:
            try:
                ctypes.windll.user32.UnregisterHotKey(None, self._registered_id)
            except Exception:
                pass
            self._registered_id = 0
        self.hotkey_id = 0
        self.backend = "none"

    def _fire(self) -> None:
        # Сигнал шлём из очереди событий, а не внутри нативного фильтра.
        QTimer.singleShot(0, self.triggered.emit)

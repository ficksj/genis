"""Системные действия Windows: мышь, клавиатура, запуск программ, яркость."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes
from typing import Any

if sys.platform == "win32":
    user32 = ctypes.WinDLL("user32", use_last_error=True)
else:  # pragma: no cover - приложение только для Windows
    user32 = None

from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key

IS_WINDOWS = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0

# --- SendInput -------------------------------------------------------------

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000

ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _INPUTunion(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTunion)]


if IS_WINDOWS:
    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    user32.GetSystemMetrics.restype = ctypes.c_int


def _send_mouse(flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> None:
    if not IS_WINDOWS:
        return
    inp = INPUT(
        type=INPUT_MOUSE,
        u=_INPUTunion(
            mi=MOUSEINPUT(
                dx=int(dx),
                dy=int(dy),
                mouseData=int(data) & 0xFFFFFFFF,
                dwFlags=int(flags),
                time=0,
                dwExtraInfo=0,
            )
        ),
    )
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


def screen_rect() -> tuple[int, int, int, int]:
    """Виртуальный рабочий стол целиком: (x, y, ширина, высота).

    Нужен для мультимониторных конфигураций: левый верхний монитор может
    начинаться с отрицательных координат.
    """
    if not IS_WINDOWS:
        return 0, 0, 1920, 1080
    x = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    y = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    width = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    height = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
    if width <= 0 or height <= 0:
        width = int(user32.GetSystemMetrics(SM_CXSCREEN))
        height = int(user32.GetSystemMetrics(SM_CYSCREEN))
        x = y = 0
    return x, y, max(1, width), max(1, height)


def set_cursor_pos(x: int, y: int) -> None:
    if IS_WINDOWS:
        user32.SetCursorPos(int(x), int(y))


def get_cursor_pos() -> tuple[int, int]:
    if not IS_WINDOWS:
        return 0, 0
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return int(point.x), int(point.y)


# --- Клавиши --------------------------------------------------------------

MODIFIERS = {
    "ctrl": Key.ctrl,
    "control": Key.ctrl,
    "alt": Key.alt,
    "shift": Key.shift,
    "win": Key.cmd,
    "cmd": Key.cmd,
    "super": Key.cmd,
    "meta": Key.cmd,
}

SPECIAL_KEYS = {
    "space": Key.space,
    "tab": Key.tab,
    "enter": Key.enter,
    "return": Key.enter,
    "esc": Key.esc,
    "escape": Key.esc,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "del": Key.delete,
    "insert": Key.insert,
    "home": Key.home,
    "end": Key.end,
    "pageup": Key.page_up,
    "pagedown": Key.page_down,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "capslock": Key.caps_lock,
    "printscreen": Key.print_screen,
    "pause": Key.pause,
    "menu": Key.menu,
    "play": Key.media_play_pause,
    "next": Key.media_next,
    "prev": Key.media_previous,
    "volume_up": Key.media_volume_up,
    "volume_down": Key.media_volume_down,
    "mute": Key.media_volume_mute,
    **{f"f{i}": getattr(Key, f"f{i}") for i in range(1, 21)},
}

MEDIA_KEYS = {
    "play_pause": Key.media_play_pause,
    "next": Key.media_next,
    "prev": Key.media_previous,
    "volume_up": Key.media_volume_up,
    "volume_down": Key.media_volume_down,
    "mute": Key.media_volume_mute,
}

MEDIA_LABELS = {
    "play_pause": "Play / Pause",
    "next": "Следующий трек",
    "prev": "Предыдущий трек",
    "volume_up": "Громкость +",
    "volume_down": "Громкость −",
    "mute": "Выключить звук",
}

WINDOW_SHORTCUTS = {
    "alt_tab": "alt+tab",
    "show_desktop": "win+d",
    "task_view": "win+tab",
    "explorer": "win+e",
    "close": "alt+f4",
    "snap_left": "win+left",
    "snap_right": "win+right",
    "maximize": "win+up",
    "minimize": "win+down",
    "desktop_left": "ctrl+win+left",
    "desktop_right": "ctrl+win+right",
    "lock": "win+l",
    "screenshot": "win+shift+s",
    "settings": "win+i",
    "search": "win+s",
    "run": "win+r",
}

WINDOW_LABELS = {
    "alt_tab": "Alt+Tab — переключить окно",
    "show_desktop": "Win+D — свернуть все окна",
    "task_view": "Win+Tab — все окна",
    "explorer": "Win+E — проводник",
    "close": "Alt+F4 — закрыть окно",
    "snap_left": "Win+← — окно влево",
    "snap_right": "Win+→ — окно вправо",
    "maximize": "Win+↑ — развернуть окно",
    "minimize": "Win+↓ — свернуть окно",
    "desktop_left": "Ctrl+Win+← — рабочий стол влево",
    "desktop_right": "Ctrl+Win+→ — рабочий стол вправо",
    "lock": "Win+L — заблокировать ПК",
    "screenshot": "Win+Shift+S — фрагмент экрана",
    "settings": "Win+I — параметры Windows",
    "search": "Win+S — поиск",
    "run": "Win+R — выполнить",
}

BUTTON_LABELS = {"left": "левая", "right": "правая", "middle": "средняя"}
BUTTON_FLAGS = {
    "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}


def parse_hotkey(combo: str) -> tuple[list[Any], Any | None]:
    """'ctrl+alt+q' -> ([Key.ctrl, Key.alt], 'q')."""
    parts = [p.strip().lower() for p in (combo or "").split("+") if p.strip()]
    modifiers: list[Any] = []
    key: Any | None = None
    for part in parts:
        if part in MODIFIERS:
            modifiers.append(MODIFIERS[part])
            continue
        if part in SPECIAL_KEYS:
            key = SPECIAL_KEYS[part]
        elif len(part) == 1:
            key = part
        else:
            try:
                key = Key[part]
            except KeyError:
                key = None
    return modifiers, key


class SystemController:
    """Все действия над системой. Один экземпляр на приложение."""

    def __init__(self) -> None:
        self.keyboard = KeyboardController()
        self._brightness: int | None = None
        self._brightness_supported: bool | None = None
        self._last_media = 0.0

    # --- мышь ---
    def mouse_down(self, button: str = "left") -> None:
        down, _ = BUTTON_FLAGS.get(button, BUTTON_FLAGS["left"])
        _send_mouse(down)

    def mouse_up(self, button: str = "left") -> None:
        _, up = BUTTON_FLAGS.get(button, BUTTON_FLAGS["left"])
        _send_mouse(up)

    def click(self, button: str = "left", double: bool = False) -> None:
        down, up = BUTTON_FLAGS.get(button, BUTTON_FLAGS["left"])
        _send_mouse(down)
        _send_mouse(up)
        if double:
            time.sleep(0.03)
            _send_mouse(down)
            _send_mouse(up)

    def scroll(self, steps: int, horizontal: bool = False) -> None:
        if not steps:
            return
        flag = MOUSEEVENTF_HWHEEL if horizontal else MOUSEEVENTF_WHEEL
        # Windows ждёт «щелчки» по 120 единиц; большие значения режем на части.
        while steps:
            chunk = max(-600, min(600, steps))
            _send_mouse(flag, data=chunk * 120)
            steps -= chunk

    # --- клавиатура ---
    def press_hotkey(self, combo: str) -> None:
        modifiers, key = parse_hotkey(combo)
        if key is None:
            return
        for mod in modifiers:
            self.keyboard.press(mod)
        if modifiers:
            time.sleep(0.012)
        self.keyboard.press(key)
        self.keyboard.release(key)
        if modifiers:
            time.sleep(0.012)
        for mod in reversed(modifiers):
            self.keyboard.release(mod)

    def press_key(self, name: str) -> None:
        key = SPECIAL_KEYS.get(name.lower())
        if key is not None:
            self.keyboard.press(key)
            self.keyboard.release(key)

    def type_text(self, text: str) -> None:
        if text:
            self.keyboard.type(text)

    def media(self, key: str) -> None:
        key_obj = MEDIA_KEYS.get(key)
        if key_obj is None:
            return
        # Не спамим, если несколько кадров подряд.
        now = time.perf_counter()
        if now - self._last_media < 0.05:
            return
        self._last_media = now
        self.keyboard.press(key_obj)
        self.keyboard.release(key_obj)

    # --- яркость ---
    def _powershell(self, script: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=CREATE_NO_WINDOW,
        )

    def get_brightness(self) -> int | None:
        if self._brightness_supported is False:
            return None
        if self._brightness is not None:
            return self._brightness
        if not IS_WINDOWS:
            return None
        try:
            res = self._powershell(
                "(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness).CurrentBrightness"
            )
            value = int((res.stdout or "").strip().splitlines()[0])
            self._brightness = max(0, min(100, value))
            self._brightness_supported = True
            return self._brightness
        except Exception:
            self._brightness_supported = False
            return None

    def brightness_step(self, delta: int) -> str | None:
        current = self.get_brightness()
        if current is None:
            return "Яркость не поддерживается этим монитором (обычно так на ПК-мониторах)"
        value = max(0, min(100, current + int(delta)))
        self._brightness = value
        try:
            self._powershell(
                "(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods)"
                f".WmiSetBrightness(1,{value})"
            )
        except Exception as exc:  # pragma: no cover - зависит от железа
            return f"Не удалось изменить яркость: {exc}"
        return None

    def set_brightness(self, value: int) -> str | None:
        current = self.get_brightness()
        if current is None:
            return "Яркость не поддерживается этим монитором"
        return self.brightness_step(int(value) - current)

    # --- запуск ---
    def launch(self, target: str) -> str | None:
        target = os.path.expandvars(os.path.expanduser((target or "").strip().strip('"')))
        if not target:
            return "Не указан путь или ссылка"
        try:
            if target.lower().startswith(("http://", "https://")):
                os.startfile(target)  # noqa: S606
            elif os.path.exists(target):
                os.startfile(target)  # noqa: S606
            elif "://" in target:
                os.startfile(target)  # noqa: S606
            else:
                subprocess.Popen(
                    ["cmd", "/c", "start", "", target],
                    creationflags=CREATE_NO_WINDOW,
                    shell=False,
                )
        except OSError as exc:
            return f"Не удалось запустить «{target}»: {exc}"
        return None

    def window(self, command: str) -> None:
        combo = WINDOW_SHORTCUTS.get(command)
        if combo:
            self.press_hotkey(combo)

    def run_command(self, command: str) -> str | None:
        if not command.strip():
            return "Пустая команда"
        try:
            subprocess.Popen(command, shell=True)
        except OSError as exc:
            return f"Команда не запустилась: {exc}"
        return None

    # --- автозапуск ---
    @staticmethod
    def autostart_command() -> str:
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        run_py = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "run.py")
        return f'"{pythonw}" "{run_py}"'

    def set_autostart(self, enabled: bool) -> bool:
        if not IS_WINDOWS:
            return False
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
            ) as key:
                if enabled:
                    winreg.SetValueEx(key, "Genis", 0, winreg.REG_SZ, self.autostart_command())
                else:
                    try:
                        winreg.DeleteValue(key, "Genis")
                    except FileNotFoundError:
                        pass
            return True
        except OSError:
            return False

    @staticmethod
    def is_autostart_enabled() -> bool:
        if not IS_WINDOWS:
            return False
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_QUERY_VALUE,
            ) as key:
                winreg.QueryValueEx(key, "Genis")
                return True
        except OSError:
            return False

"""Шрифты приложения.

Manrope и JetBrains Mono лежат в `assets/fonts` (OFL), поэтому интерфейс
выглядит одинаково на любой Windows. Если файлов нет — откат на системные.
"""

from __future__ import annotations

from PySide6.QtGui import QFontDatabase

from ..paths import assets_dir

UI_FAMILY = "Manrope"
MONO_FAMILY = "JetBrains Mono"

_loaded = False
_ui_family = "Segoe UI"
_mono_family = "Consolas"


def load_fonts() -> tuple[str, str]:
    """Регистрирует шрифты в Qt. Возвращает (ui, mono) — реальные семейства."""
    global _loaded, _ui_family, _mono_family
    if _loaded:
        return _ui_family, _mono_family

    folder = assets_dir() / "fonts"
    if folder.is_dir():
        for path in sorted(folder.glob("*.ttf")):
            QFontDatabase.addApplicationFont(str(path))

    families = {name.lower() for name in QFontDatabase.families()}
    _ui_family = UI_FAMILY if UI_FAMILY.lower() in families else "Segoe UI"
    _mono_family = MONO_FAMILY if MONO_FAMILY.lower() in families else "Consolas"
    _loaded = True
    return _ui_family, _mono_family


def ui_family() -> str:
    return load_fonts()[0]


def mono_family() -> str:
    return load_fonts()[1]


__all__ = ["load_fonts", "ui_family", "mono_family", "UI_FAMILY", "MONO_FAMILY"]

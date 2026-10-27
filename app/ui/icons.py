"""Иконки приложения.

Пиксельная обезьяна и значки живут в `logo.py`; этот модуль — короткий фасад,
чтобы остальной код продолжал импортировать `app_icon` / `tray_icon`.
"""

from __future__ import annotations

from .logo import app_icon, badge_pixmap, circle_pixmap, monkey_pixmap, tray_icon

__all__ = ["app_icon", "tray_icon", "badge_pixmap", "circle_pixmap", "monkey_pixmap"]

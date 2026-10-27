"""Список камер Windows.

Имена и порядок берём из DirectShow через `pygrabber`: порядок совпадает с
индексами OpenCV (`cv2.VideoCapture(index, cv2.CAP_DSHOW)`), поэтому имя можно
однозначно превратить в индекс. Если pygrabber недоступен, остаётся проверка
индексов «открывается / не открывается» и подписи «Камера N».
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

IS_WINDOWS = sys.platform == "win32"


@dataclass
class CameraDevice:
    index: int
    name: str

    @property
    def label(self) -> str:
        return f"{self.name}  ·  {self.index}"


def _from_directshow() -> list[CameraDevice]:
    try:
        from pygrabber.dshow_graph import FilterGraph
    except Exception:
        return []
    try:
        names = FilterGraph().get_input_devices()
    except Exception:
        return []
    return [CameraDevice(index=i, name=name) for i, name in enumerate(names)]


def _probe_devices(limit: int = 6) -> list[CameraDevice]:
    """Резерв: какие индексы реально открываются."""
    try:
        import cv2
    except Exception:
        return []
    found: list[CameraDevice] = []
    for index in range(limit):
        capture = None
        try:
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if capture is not None and capture.isOpened():
                ok, _frame = capture.read()
                if ok:
                    found.append(CameraDevice(index=index, name=f"Камера {index}"))
        except Exception:
            continue
        finally:
            if capture is not None:
                try:
                    capture.release()
                except Exception:
                    pass
    return found


def list_cameras(probe_fallback: bool = True) -> list[CameraDevice]:
    """Все камеры по порядку индексов OpenCV."""
    if not IS_WINDOWS:
        return []
    devices = _from_directshow()
    if not devices and probe_fallback:
        devices = _probe_devices()
    return devices


def resolve_index(name: str, fallback: int = 0) -> int:
    """Индекс камеры по имени; если камеру переставили — сохранённый номер."""
    name = (name or "").strip()
    fallback = max(0, int(fallback))
    if not name:
        return fallback
    for device in list_cameras(probe_fallback=False):
        if device.name.strip().lower() == name.lower():
            return device.index
    return fallback


__all__ = ["CameraDevice", "list_cameras", "resolve_index"]

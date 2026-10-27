"""Пути приложения: конфиг, логи, модель MediaPipe."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Genis"

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_MIN_BYTES = 1_000_000


def app_dir() -> Path:
    """Папка с кодом (или с .exe в собранной версии)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundle_dir() -> Path:
    """Папка ресурсов внутри сборки PyInstaller."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", app_dir()))
    return app_dir()


def assets_dir() -> Path:
    """Ресурсы приложения: шрифты, иконки, логотип."""
    return bundle_dir() / "assets"


def data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    override = os.environ.get("GENIS_CONFIG")
    if override:
        return Path(override).expanduser()
    return data_dir() / "config.json"


def log_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_path() -> Path:
    return log_dir() / "genis.log"


def model_path() -> Path:
    override = os.environ.get("GENIS_MODEL")
    if override:
        return Path(override).expanduser()
    path = data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path / "hand_landmarker.task"


def ensure_model(progress=None) -> Path:
    """Скачивает модель распознавания руки, если её ещё нет.

    progress(downloaded_bytes, total_bytes) вызывается по мере загрузки.
    """
    target = model_path()
    if target.exists() and target.stat().st_size >= MODEL_MIN_BYTES:
        return target

    bundled = bundle_dir() / "assets" / "hand_landmarker.task"
    if bundled.exists() and bundled.stat().st_size >= MODEL_MIN_BYTES:
        target.write_bytes(bundled.read_bytes())
        return target

    import urllib.request

    tmp = target.with_suffix(".part")
    tmp.unlink(missing_ok=True)

    def hook(blocks: int, block_size: int, total: int) -> None:
        if progress is not None:
            progress(min(blocks * block_size, total or 0), total or 0)

    try:
        urllib.request.urlretrieve(MODEL_URL, tmp, reporthook=hook)  # noqa: S310
    except Exception:
        # На некоторых машинах OpenSSL отвергает сертификат Google
        # («certificate key too weak»). Пробуем системные загрузчики.
        tmp.unlink(missing_ok=True)
        _download_with_system_tools(MODEL_URL, tmp, progress)

    if not tmp.exists() or tmp.stat().st_size < MODEL_MIN_BYTES:
        raise RuntimeError("Скачанный файл модели повреждён или пуст")
    tmp.replace(target)
    return target


def _download_with_system_tools(url: str, target: Path, progress=None) -> None:
    """Запасной путь загрузки: curl.exe или PowerShell (системный TLS)."""
    import shutil
    import subprocess

    creation_flags = 0x08000000 if sys.platform == "win32" else 0
    curl = shutil.which("curl")
    if curl:
        subprocess.run(
            [curl, "-L", "--fail", "--silent", "--show-error", "-o", str(target), url],
            check=True,
            timeout=300,
            creationflags=creation_flags,
        )
        if progress is not None:
            size = target.stat().st_size if target.exists() else 0
            progress(size, size)
        return

    if sys.platform == "win32":
        script = (
            "$ProgressPreference='SilentlyContinue';"
            f"Invoke-WebRequest -Uri '{url}' -OutFile '{target}' -UseBasicParsing"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            check=True,
            timeout=300,
            creationflags=creation_flags,
        )
        if progress is not None:
            size = target.stat().st_size if target.exists() else 0
            progress(size, size)
        return

    raise RuntimeError("Не удалось скачать модель: нет доступного загрузчика")

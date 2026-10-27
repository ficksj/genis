"""Поток камеры: захват, MediaPipe, отрисовка превью, вызовы движка."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from .engine import EngineState, GestureEngine
from .features import HAND_CONNECTIONS, Hand, points_from_landmarks


@dataclass
class FrameReport:
    hand: Hand | None
    state: EngineState
    fps: float
    hands: list[Hand] = field(default_factory=list)


class CameraWorker(QThread):
    preview = Signal(QImage)
    report = Signal(object)          # FrameReport
    status = Signal(dict)
    log = Signal(str)
    failed = Signal(str)

    def __init__(self, cfg: dict[str, Any], engine: GestureEngine, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.engine = engine
        self._stop_event = threading.Event()
        self._preview_last = 0.0
        self._status_last = 0.0
        self._fps_times: list[float] = []

    def request_stop(self) -> None:
        self._stop_event.set()

    # --- создание MediaPipe ----------------------------------------------
    @staticmethod
    def _create_landmarker(model_path: str, cfg: dict[str, Any]):
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision

        base = mp_python.BaseOptions(model_asset_path=model_path)
        tracking = cfg.get("tracking", {})
        options = mp_vision.HandLandmarkerOptions(
            base_options=base,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=max(1, int(tracking.get("max_hands", 2))),
            min_hand_detection_confidence=float(tracking.get("min_detection", 0.6)),
            min_hand_presence_confidence=float(tracking.get("min_presence", 0.5)),
            min_tracking_confidence=float(tracking.get("min_tracking", 0.5)),
        )
        return mp_vision.HandLandmarker.create_from_options(options)

    def run(self) -> None:  # noqa: C901
        import cv2
        import mediapipe as mp

        from ..paths import model_path

        camera = self.cfg.get("camera", {})
        index = int(camera.get("index", 0))
        width = int(camera.get("width", 640))
        height = int(camera.get("height", 480))
        fps_target = int(camera.get("fps", 30))
        mirror = bool(camera.get("mirror", True))

        try:
            landmarker = self._create_landmarker(str(model_path()), self.cfg)
        except Exception as exc:
            self.failed.emit(f"Не удалось загрузить модель MediaPipe: {exc}")
            return

        cap = None
        warned = False
        while not self._stop_event.is_set() and cap is None:
            for backend in (cv2.CAP_DSHOW, cv2.CAP_ANY):
                try:
                    candidate = cv2.VideoCapture(index, backend)
                except Exception:
                    candidate = None
                if candidate is not None and candidate.isOpened():
                    cap = candidate
                    break
                if candidate is not None:
                    candidate.release()
            if cap is None:
                if not warned:
                    self.failed.emit(
                        f"Камера {index} не найдена или занята другой программой"
                    )
                    warned = True
                for _ in range(20):
                    if self._stop_event.is_set():
                        break
                    time.sleep(0.1)
                if self._stop_event.is_set():
                    self._close(landmarker, None)
                    return

        if cap is None:
            self._close(landmarker, None)
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps_target)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.log.emit(f"Камера {index} запущена ({width}x{height})")

        start = time.perf_counter()
        last_ts = 0
        fail_count = 0

        try:
            while not self._stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    fail_count += 1
                    if fail_count > 40:
                        self.failed.emit("Камера перестала отдавать кадры")
                        break
                    time.sleep(0.02)
                    continue
                fail_count = 0

                if mirror:
                    frame = cv2.flip(frame, 1)

                height_px, width_px = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                timestamp = int((time.perf_counter() - start) * 1000)
                if timestamp <= last_ts:
                    timestamp = last_ts + 1
                last_ts = timestamp

                try:
                    result = landmarker.detect_for_video(mp_image, timestamp)
                except Exception as exc:  # pragma: no cover - сбой модели
                    self.failed.emit(f"Ошибка распознавания: {exc}")
                    break

                hands = self._pick_hands(result, width_px, height_px)
                now = time.perf_counter()
                state = self.engine.process(hands, now)

                if camera.get("show_landmarks", True):
                    for hand in hands:
                        self._draw(frame, hand)

                self._fps_times.append(now)
                if len(self._fps_times) > 45:
                    self._fps_times.pop(0)
                fps = 0.0
                if len(self._fps_times) > 2:
                    span = self._fps_times[-1] - self._fps_times[0]
                    if span > 0:
                        fps = (len(self._fps_times) - 1) / span

                self.report.emit(
                    FrameReport(
                        hand=hands[0] if hands else None,
                        state=state,
                        fps=fps,
                        hands=hands,
                    )
                )

                if now - self._preview_last >= 0.05:
                    self._preview_last = now
                    self.preview.emit(self._to_qimage(frame))

                if now - self._status_last >= 0.4:
                    self._status_last = now
                    self.status.emit(
                        {
                            "fps": round(fps, 1),
                            "hand": bool(hands),
                            "hands": len(hands),
                            "gesture": state.gesture,
                            "confidence": round(state.confidence, 2),
                            "active": state.active,
                            "paused": state.paused,
                            "camera": index,
                            "resolution": f"{width_px}x{height_px}",
                        }
                    )
        finally:
            self._close(landmarker, cap)

    @staticmethod
    def _pick_hands(result, width: int, height: int) -> list[Hand]:
        """Все руки в кадре, начиная с самой крупной (ближней)."""
        if not result.hand_landmarks:
            return []
        hands: list[Hand] = []
        for i, landmarks in enumerate(result.hand_landmarks):
            points = points_from_landmarks(landmarks, width, height)
            handedness = ""
            try:
                handedness = result.handedness[i][0].category_name
            except (IndexError, AttributeError):
                pass
            hands.append(
                Hand(points=points, width=width, height=height, handedness=handedness)
            )
        hands.sort(key=lambda hand: hand.palm_size, reverse=True)
        return hands

    @staticmethod
    def _draw(frame: np.ndarray, hand: Hand) -> None:
        import cv2

        pts = hand.points[:, :2].astype(int)
        for a, b in HAND_CONNECTIONS:
            cv2.line(frame, tuple(pts[a]), tuple(pts[b]), (90, 200, 120), 2, cv2.LINE_AA)
        for i, (x, y) in enumerate(pts):
            color = (60, 120, 255) if i in (4, 8, 12, 16, 20) else (240, 240, 240)
            cv2.circle(frame, (int(x), int(y)), 4, color, -1, cv2.LINE_AA)

    @staticmethod
    def _to_qimage(frame: np.ndarray) -> QImage:
        height, width = frame.shape[:2]
        image = QImage(
            frame.data,
            width,
            height,
            int(frame.strides[0]),
            QImage.Format.Format_BGR888,
        )
        return image.copy()

    @staticmethod
    def _close(landmarker, cap) -> None:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
        if landmarker is not None:
            try:
                landmarker.close()
            except Exception:
                pass

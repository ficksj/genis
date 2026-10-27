"""Сглаживание курсора (фильтр One Euro)."""

from __future__ import annotations

import math


class _LowPass:
    def __init__(self) -> None:
        self.value: float | None = None

    def __call__(self, x: float, alpha: float) -> float:
        if self.value is None:
            self.value = x
        else:
            self.value = alpha * x + (1.0 - alpha) * self.value
        return self.value

    def reset(self) -> None:
        self.value = None


class OneEuroFilter:
    """Быстрый и стабильный фильтр для «дрожащих» координат.

    mincutoff — насколько сильно сглаживать в покое,
    beta      — насколько меньше сглаживать при быстром движении.
    """

    def __init__(self, mincutoff: float = 1.0, beta: float = 0.7, dcutoff: float = 1.0) -> None:
        self.mincutoff = float(mincutoff)
        self.beta = float(beta)
        self.dcutoff = float(dcutoff)
        self._x = _LowPass()
        self._dx = _LowPass()
        self._prev: float | None = None
        self._prev_t: float | None = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * max(cutoff, 1e-6))
        return 1.0 / (1.0 + tau / max(dt, 1e-6))

    def __call__(self, x: float, dt: float) -> float:
        if self._prev is None or self._prev_t is None:
            self._prev = x
            self._prev_t = dt
            self._x.value = x
            self._dx.value = 0.0
            return x

        dt = max(dt, 1e-3)
        dx = (x - self._prev) / dt
        dx_hat = self._dx(dx, self._alpha(self.dcutoff, dt))
        cutoff = self.mincutoff + self.beta * abs(dx_hat)
        x_hat = self._x(x, self._alpha(cutoff, dt))
        self._prev = x
        return x_hat

    def reset(self) -> None:
        self._x.reset()
        self._dx.reset()
        self._prev = None
        self._prev_t = None

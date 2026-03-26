from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class RateLimitConfig:
    enabled: bool = True
    window_seconds: int = 10
    max_events_per_window: int = 3


class FixedWindowRateLimiter:
    def __init__(
        self,
        config: RateLimitConfig,
        now_provider: Callable[[], float] | None = None,
    ) -> None:
        self.config = config
        self._now = now_provider or time.time
        self._window_id: int | None = None
        self._count = 0

    def allow(self) -> bool:
        if not self.config.enabled:
            return True

        window_seconds = max(1, int(self.config.window_seconds))
        max_events = max(1, int(self.config.max_events_per_window))
        current_window_id = int(self._now() // window_seconds)

        if self._window_id != current_window_id:
            self._window_id = current_window_id
            self._count = 0

        if self._count >= max_events:
            return False

        self._count += 1
        return True

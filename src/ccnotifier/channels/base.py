from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseChannel(ABC):
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def validate_config(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def send_notification(self, event: Dict[str, Any]) -> bool:
        raise NotImplementedError

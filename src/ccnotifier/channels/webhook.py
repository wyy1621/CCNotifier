from __future__ import annotations

from typing import Any, Dict

from .base import BaseChannel


class WebhookChannel(BaseChannel):
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.url = str(config.get("url", ""))
        self.timeout_seconds = int(config.get("timeout_seconds", 10))

    def validate_config(self) -> bool:
        return bool(self.url)

    def send_notification(self, event: Dict[str, Any]) -> bool:
        if not self.validate_config():
            self.logger.error("Webhook 渠道缺少 url")
            return False

        try:
            import requests
        except ImportError:
            self.logger.error("Webhook 渠道需要 requests 依赖")
            return False

        response = requests.post(self.url, json=event, timeout=self.timeout_seconds)
        if 200 <= response.status_code < 300:
            return True

        self.logger.error("Webhook 发送失败: HTTP %s", response.status_code)
        return False

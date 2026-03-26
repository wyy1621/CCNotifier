from __future__ import annotations

import logging
from typing import Dict

from ..channels import get_channel_class
from .config import AppConfig
from .events import NotificationEvent
from .rate_limit import FixedWindowRateLimiter


class Notifier:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.rate_limiter = FixedWindowRateLimiter(config.rate_limit)
        self.channels = self._init_channels()

    def send_event(self, event: NotificationEvent) -> bool:
        if not self.rate_limiter.allow():
            self.logger.info("通知被限流丢弃: %s", event.name)
            return False

        channel_names = self.config.channels_for_event(event.name)
        if not channel_names:
            self.logger.warning("事件未配置通知渠道: %s", event.name)
            return False

        payload = event.to_dict()
        success = False
        for channel_name in channel_names:
            channel = self.channels.get(channel_name)
            if channel is None:
                self.logger.warning("渠道未启用或不存在: %s", channel_name)
                continue
            if channel.send_notification(payload):
                success = True
            else:
                self.logger.error("通知发送失败: %s", channel_name)
        return success

    def _init_channels(self) -> Dict[str, object]:
        channels: Dict[str, object] = {}
        for channel_name, channel_config in self.config.channels.items():
            if not channel_config.get("enabled", False):
                continue
            channel_class = get_channel_class(channel_name)
            if channel_class is None:
                self.logger.warning("未知渠道: %s", channel_name)
                continue
            channels[channel_name] = channel_class(channel_config)
        return channels

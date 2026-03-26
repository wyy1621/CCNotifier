from .base import BaseChannel
from .telegram import TelegramChannel
from .webhook import WebhookChannel

CHANNEL_REGISTRY = {
    "telegram": TelegramChannel,
    "webhook": WebhookChannel,
}


def get_channel_class(name: str):
    return CHANNEL_REGISTRY.get(name)


__all__ = [
    "BaseChannel",
    "TelegramChannel",
    "WebhookChannel",
    "CHANNEL_REGISTRY",
    "get_channel_class",
]

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

from .rate_limit import RateLimitConfig

DEFAULT_CONFIG_PATH = Path.home() / ".ccnotifier" / "config.yaml"


@dataclass(slots=True)
class AppConfig:
    default_channels: list[str] = field(default_factory=lambda: ["telegram"])
    events: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    channels: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    config_path: Path = DEFAULT_CONFIG_PATH

    def channels_for_event(self, event_name: str) -> list[str]:
        event_config = self.events.get(event_name, {})
        event_channels = event_config.get("channels")
        if isinstance(event_channels, list) and event_channels:
            return [str(channel) for channel in event_channels]
        return list(self.default_channels)


DEFAULT_CONFIG: Dict[str, Any] = {
    "default_channels": ["telegram"],
    "events": {
        "permission-needed": {"channels": ["telegram"]},
        "claude-stopped": {"channels": ["telegram"]},
        "sensitive-operation": {"channels": ["telegram"]},
        "idle-prompt": {"channels": ["telegram"]},
    },
    "channels": {
        "telegram": {
            "enabled": False,
            "bot_token": "",
            "chat_id": "",
            "parse_mode": "Markdown",
            "timeout_seconds": 10,
            "proxy_url": "",
        },
        "webhook": {
            "enabled": False,
            "url": "",
            "timeout_seconds": 10,
        },
    },
    "rate_limit": {
        "enabled": True,
        "window_seconds": 10,
        "max_events_per_window": 3,
        "scope": "global",
    },
}


def load_config(config_path: str | Path | None = None) -> AppConfig:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    data = _deep_copy(DEFAULT_CONFIG)

    if path.exists():
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("PyYAML is required to load config files") from exc

        with path.open("r", encoding="utf-8") as file:
            loaded = yaml.safe_load(file) or {}
        if not isinstance(loaded, dict):
            raise ValueError("Config file must contain a YAML object")
        data = _deep_merge(data, loaded)

    rate_limit_data = data.get("rate_limit", {})
    return AppConfig(
        default_channels=[str(channel) for channel in data.get("default_channels", ["telegram"])],
        events=data.get("events", {}),
        channels=data.get("channels", {}),
        rate_limit=RateLimitConfig(
            enabled=bool(rate_limit_data.get("enabled", True)),
            window_seconds=int(rate_limit_data.get("window_seconds", 10)),
            max_events_per_window=int(rate_limit_data.get("max_events_per_window", 3)),
        ),
        config_path=path,
    )


def ensure_parent_dir(path: str | Path | None = None) -> Path:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    return config_path.parent


def render_default_config() -> str:
    return """default_channels:
  - telegram # 默认通知渠道，事件未单独指定时走这里

events:
  permission-needed:
    channels: [telegram] # 权限请求通知走 Telegram
  claude-stopped:
    channels: [telegram] # Claude 停止并等待用户查看/继续时通知
  sensitive-operation:
    channels: [telegram] # 命中高风险 Bash 模式时通知
  idle-prompt:
    channels: [telegram] # 预留扩展位，首版不启用

channels:
  telegram:
    enabled: false # 是否启用 Telegram 渠道
    bot_token: \"\" # Telegram Bot token
    chat_id: \"\" # 接收通知的 chat id
    parse_mode: Markdown # 消息格式，首版默认 Markdown
    timeout_seconds: 10 # 请求超时秒数
    proxy_url: \"\" # 可选代理地址，例如 http://127.0.0.1:7890

  webhook:
    enabled: false # 第二优先级渠道，首版默认关闭
    url: \"\" # Webhook 地址
    timeout_seconds: 10 # 请求超时秒数

rate_limit:
  enabled: true # 是否启用基础限流
  window_seconds: 10 # 固定统计时间窗，例如 10 秒
  max_events_per_window: 3 # 单个时间窗内最多允许发送 3 条通知
  scope: global # 首版按全局总量限流，不区分渠道
"""


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _deep_copy(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _deep_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_copy(item) for item in value]
    return value

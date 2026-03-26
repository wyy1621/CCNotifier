from __future__ import annotations

import time
from typing import Any, Dict

from .base import BaseChannel


class TelegramChannel(BaseChannel):
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.bot_token = str(config.get("bot_token", ""))
        self.chat_id = str(config.get("chat_id", ""))
        self.parse_mode = str(config.get("parse_mode", "Markdown"))
        self.timeout_seconds = int(config.get("timeout_seconds", 10))
        self.proxy_url = str(config.get("proxy_url", "")).strip()
        self.auto_delete_after_seconds = self._normalize_auto_delete_seconds(config.get("auto_delete_after_seconds", 0))
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    def validate_config(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_notification(self, event: Dict[str, Any]) -> bool:
        if not self.validate_config():
            self.logger.error("Telegram 渠道缺少 bot_token 或 chat_id")
            return False
        if self.proxy_url.startswith("socks"):
            self.logger.error("Telegram 渠道仅支持 HTTP/HTTPS 代理，不支持 SOCKS")
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": self._format_message(event),
            "parse_mode": self.parse_mode,
            "disable_web_page_preview": True,
        }

        try:
            import requests
        except ImportError:
            self.logger.error("Telegram 渠道需要 requests 依赖")
            return False

        response = requests.post(
            f"{self.api_url}/sendMessage",
            **self._request_kwargs(payload),
        )
        if response.status_code != 200:
            self.logger.error("Telegram API 请求失败: HTTP %s", response.status_code)
            return False

        result = response.json()
        if not result.get("ok"):
            self.logger.error("Telegram 通知发送失败: %s", result)
            return False

        message_id = self._extract_message_id(result)
        if self.auto_delete_after_seconds > 0 and message_id is not None:
            self.logger.debug(
                "Telegram 消息发送成功，message_id=%s，准备在 %s 秒后同步撤回",
                message_id,
                self.auto_delete_after_seconds,
            )
            self._delete_message_after_delay(message_id)
        elif self.auto_delete_after_seconds > 0:
            self.logger.warning("Telegram 消息发送成功但缺少 message_id，跳过自动撤回")
        return True

    def _request_kwargs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request_kwargs: Dict[str, Any] = {
            "json": payload,
            "timeout": self.timeout_seconds,
        }
        if self.proxy_url:
            request_kwargs["proxies"] = {
                "http": self.proxy_url,
                "https": self.proxy_url,
            }
        return request_kwargs

    def _extract_message_id(self, result: Dict[str, Any]) -> int | None:
        message = result.get("result")
        if not isinstance(message, dict):
            return None
        message_id = message.get("message_id")
        return message_id if isinstance(message_id, int) else None

    def _delete_message_after_delay(self, message_id: int) -> None:
        self.logger.debug("Telegram 自动撤回等待开始，message_id=%s", message_id)
        time.sleep(self.auto_delete_after_seconds)
        try:
            import requests
        except ImportError:
            self.logger.error("Telegram 渠道需要 requests 依赖")
            return

        payload = {
            "chat_id": self.chat_id,
            "message_id": message_id,
        }
        try:
            self.logger.debug("Telegram 开始调用 deleteMessage，message_id=%s", message_id)
            response = requests.post(
                f"{self.api_url}/deleteMessage",
                **self._request_kwargs(payload),
            )
            if response.status_code != 200:
                self.logger.error("Telegram 删除消息失败: HTTP %s", response.status_code)
                return

            result = response.json()
            if not result.get("ok"):
                self.logger.error("Telegram 删除消息失败: %s", result)
                return
        except Exception:
            self.logger.exception("Telegram 删除消息时发生异常，message_id=%s", message_id)
            return

        self.logger.debug("Telegram 删除消息成功，message_id=%s", message_id)

    def _format_message(self, event: Dict[str, Any]) -> str:
        event_name = event.get("name", "notification")
        project_name = event.get("project_name", "unknown")
        summary = event.get("summary", "")
        details = event.get("details", {})

        if event_name == "user-interaction-needed":
            return self._format_user_interaction_message(event, project_name, details)

        if event_name == "claude-stopped":
            reason = self._escape(str(details.get("reason", "")))
            stop_hook_name = self._escape(str(details.get("stop_hook_name", "Stop")))
            return (
                "✅ *Claude Code 已停止*\n\n"
                f"*项目*: `{self._escape(project_name)}`\n"
                f"*摘要*: {self._escape(summary)}\n"
                f"*原因*: {reason}\n"
                f"*Hook*: `{stop_hook_name}`"
            )

        if event_name == "sensitive-operation":
            matched_rule = self._escape(str(details.get("matched_rule", "")))
            command_preview = self._escape(str(details.get("command_preview", "")))
            return (
                "⚠️ *Claude Code 即将执行高风险操作*\n\n"
                f"*项目*: `{self._escape(project_name)}`\n"
                f"*规则*: `{matched_rule}`\n"
                f"*命令预览*: `{command_preview}`"
            )

        return (
            "📣 *Claude Code 通知*\n\n"
            f"*项目*: `{self._escape(project_name)}`\n"
            f"*摘要*: {self._escape(summary)}"
        )

    def _format_user_interaction_message(self, event: Dict[str, Any], project_name: Any, details: Dict[str, Any]) -> str:
        notification_type = str(details.get("notification_type", ""))
        prompt = str(details.get("prompt", "")).strip()
        tool_name = str(details.get("tool_name", "")).strip()
        preview = str(details.get("tool_input_preview", "")).strip()
        trigger_event = str(event.get("hook_event", "")).strip()

        lines = [
            "🔔 *Claude Code 需要用户交互*",
            "",
            f"*项目*: `{self._escape(str(project_name))}`",
        ]

        if notification_type == "ask_user_question":
            if prompt:
                lines.append(f"*问题*: {self._escape(prompt)}")
            if preview:
                lines.append(f"*补充*: {self._escape(preview)}")
            if tool_name:
                lines.append(f"*工具*: `{self._escape(tool_name)}`")
            return "\n".join(lines)

        if tool_name:
            lines.append(f"*工具*: `{self._escape(tool_name)}`")
        if trigger_event:
            lines.append(f"*触发事件*: `{self._escape(trigger_event)}`")
        if prompt:
            lines.append(f"*提示*: {self._escape(prompt)}")
        if preview:
            lines.append(f"*输入预览*: `{self._escape(preview)}`")
        return "\n".join(lines)

    def _normalize_auto_delete_seconds(self, value: Any) -> int:
        try:
            seconds = int(value)
        except (TypeError, ValueError):
            seconds = 0
        if seconds < 0:
            return 0
        if seconds > 10:
            return 10
        return seconds

    def _escape(self, value: str) -> str:
        escape_chars = "_*[]()~`>#+-=|{}.!"
        escaped = []
        for char in value:
            if char in escape_chars:
                escaped.append("\\" + char)
            else:
                escaped.append(char)
        return "".join(escaped)

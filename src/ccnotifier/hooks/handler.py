from __future__ import annotations

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

from ..core.config import AppConfig, load_config
from ..core.events import NotificationEvent, build_event_from_hook, extract_llm_review_input
from ..core.llm_review import LlmReviewDecision, review_command
from ..core.notifier import Notifier

SUPPORTED_HOOK_EVENTS = {"Notification", "Stop", "PreToolUse", "PermissionRequest"}
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

LOGGER = logging.getLogger("ccnotifier.hooks.handler")


def process_hook_event(
    hook_event: str,
    payload: Dict[str, Any],
    config_path: str | None = None,
    notifier: Notifier | None = None,
) -> Dict[str, Any]:
    LOGGER.debug("收到 hook 事件: %s", hook_event)
    if hook_event == "PermissionRequest":
        LOGGER.debug("PermissionRequest 原始信息: %s", _json_log(payload))
    config = load_config(config_path)
    event = build_event_from_hook(hook_event, payload)
    if event is not None:
        LOGGER.debug("规范化事件: %s", _json_log(event.to_dict()))
        active_notifier = notifier or Notifier(config)
        active_notifier.send_event(event)
        LOGGER.debug("通知已交给 notifier: %s", event.name)
    else:
        LOGGER.debug("hook 事件未映射为通知: %s", hook_event)

    if hook_event != "PermissionRequest":
        return {"continue": True}
    if not config.llm_review.enabled:
        return {"continue": True}

    review_input = extract_llm_review_input(payload)
    if review_input is None:
        return {"continue": True}

    try:
        review_result = review_command(review_input, config.llm_review)
    except Exception as exc:
        LOGGER.exception("LLM 审核失败: %s", exc)
        return {"continue": True}

    LOGGER.debug("LLM 审核结果: %s", _json_log({"decision": review_result.decision.value, "reason": review_result.reason}))
    if review_result.decision == LlmReviewDecision.DENY:
        denial_event = _build_sensitive_operation_event(payload, review_result.reason)
        active_notifier = notifier or Notifier(config)
        active_notifier.send_event(denial_event)
        LOGGER.debug("拒绝通知已交给 notifier: %s", denial_event.name)
    return _build_permission_request_response(review_result)


def _extract_hook_event(payload: Dict[str, Any]) -> str:
    hook_event = payload.get("hook_event_name")
    if isinstance(hook_event, str) and hook_event in SUPPORTED_HOOK_EVENTS:
        return hook_event

    hook_event = os.environ.get("CLAUDE_HOOK_EVENT", "")
    if hook_event in SUPPORTED_HOOK_EVENTS:
        return hook_event

    return ""


# 输入: 原始 PermissionRequest payload 和拒绝原因，输出: 敏感操作通知事件。
def _build_sensitive_operation_event(payload: Dict[str, Any], reason: str) -> NotificationEvent:
    review_input = extract_llm_review_input(payload)
    command_preview = review_input.command if review_input is not None else ""
    cwd = payload.get("cwd") or payload.get("working_directory") or os.getcwd()
    session_id = payload.get("session_id") if isinstance(payload.get("session_id"), str) else None
    return NotificationEvent(
        name="sensitive-operation",
        source="claude-code-hook",
        hook_event="PermissionRequest",
        timestamp=int(__import__("time").time()),
        session_id=session_id,
        cwd=str(cwd),
        project_name=Path(str(cwd)).resolve().name or "unknown",
        summary="Claude Code 已拒绝敏感操作",
        details={
            "tool_name": payload.get("tool_name") or payload.get("tool") or "",
            "command_preview": command_preview[:200],
            "reason": reason,
            "cwd": str(cwd),
        },
        raw=payload,
    )


# 输入: LLM 审核结果，输出: PermissionRequest hook JSON 响应；ask 时放行给 Claude 正常询问用户。
def _build_permission_request_response(result) -> Dict[str, Any]:
    if result.decision == LlmReviewDecision.ASK:
        return {"continue": True}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {
                "behavior": result.decision.value,
            },
        }
    }


def _configure_file_logging(config: AppConfig) -> Path:
    log_path = config.logging_file_path.expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    log_file = log_path.resolve()
    for handler in list(root_logger.handlers):
        if not isinstance(handler, logging.FileHandler):
            continue
        existing_path = Path(handler.baseFilename).resolve()
        if (
            existing_path == log_file
            and isinstance(handler, RotatingFileHandler)
            and handler.maxBytes == config.logging_max_bytes
            and handler.backupCount == config.logging_backup_count
        ):
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(logging.Formatter(LOG_FORMAT))
            root_logger.setLevel(logging.DEBUG)
            return log_file
        root_logger.removeHandler(handler)
        handler.close()

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=config.logging_max_bytes,
        backupCount=config.logging_backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)
    return log_file


def _json_log(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


# 输入: hook 响应对象，输出: 无；以 UTF-8 JSON 写入 stdout。
def _write_hook_response(value: Dict[str, Any]) -> None:
    output = json.dumps(value, ensure_ascii=False).encode("utf-8")
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.flush()
        return
    sys.stdout.write(output.decode("utf-8") + "\n")
    sys.stdout.flush()


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}

    config = load_config(os.environ.get("CCNOTIFIER_CONFIG"))
    _configure_file_logging(config)
    LOGGER.debug("收到原始 hook payload: %s", _json_log(payload))

    hook_event = _extract_hook_event(payload)
    LOGGER.debug("提取到 hook 事件名: %s", hook_event or "<missing>")
    if not hook_event:
        LOGGER.error("缺少 hook 事件名，stdin JSON 中未提供 hook_event_name，且环境变量 CLAUDE_HOOK_EVENT 不可用")
        _write_hook_response({"continue": True})
        return 0

    try:
        result = process_hook_event(hook_event, payload, str(config.config_path))
    except Exception as exc:
        LOGGER.exception("处理 hook 事件失败: %s", exc)
        result = {"continue": True}

    LOGGER.debug("hook 返回: %s", _json_log(result))
    _write_hook_response(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

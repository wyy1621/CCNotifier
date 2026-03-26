from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

from ..core.config import AppConfig, load_config
from ..core.events import build_event_from_hook
from ..core.notifier import Notifier

SUPPORTED_HOOK_EVENTS = {"Notification", "Stop", "PreToolUse"}
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

LOGGER = logging.getLogger("ccnotifier.hooks.handler")


def process_hook_event(
    hook_event: str,
    payload: Dict[str, Any],
    config_path: str | None = None,
    notifier: Notifier | None = None,
) -> Dict[str, Any]:
    event = build_event_from_hook(hook_event, payload)
    if event is None:
        return {"continue": True}

    active_notifier = notifier or Notifier(load_config(config_path))
    active_notifier.send_event(event)
    return {"continue": True}


def _extract_hook_event(payload: Dict[str, Any]) -> str:
    hook_event = payload.get("hook_event_name")
    if isinstance(hook_event, str) and hook_event in SUPPORTED_HOOK_EVENTS:
        return hook_event

    hook_event = os.environ.get("CLAUDE_HOOK_EVENT", "")
    if hook_event in SUPPORTED_HOOK_EVENTS:
        return hook_event

    return ""


def _configure_file_logging(config: AppConfig) -> Path:
    log_path = config.logging_file_path.expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    log_file = log_path.resolve()
    for handler in list(root_logger.handlers):
        if isinstance(handler, logging.FileHandler):
            existing_path = Path(handler.baseFilename).resolve()
            if existing_path == log_file:
                handler.setLevel(logging.INFO)
                handler.setFormatter(logging.Formatter(LOG_FORMAT))
                root_logger.setLevel(logging.INFO)
                return log_file
            root_logger.removeHandler(handler)
            handler.close()

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)
    return log_file


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}

    config = load_config(os.environ.get("CCNOTIFIER_CONFIG"))
    _configure_file_logging(config)

    hook_event = _extract_hook_event(payload)
    if not hook_event:
        LOGGER.error("缺少 hook 事件名，stdin JSON 中未提供 hook_event_name，且环境变量 CLAUDE_HOOK_EVENT 不可用")
        print(json.dumps({"continue": True}, ensure_ascii=False))
        return 0

    try:
        result = process_hook_event(hook_event, payload, str(config.config_path))
    except Exception as exc:
        LOGGER.exception("处理 hook 事件失败: %s", exc)
        result = {"continue": True}

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

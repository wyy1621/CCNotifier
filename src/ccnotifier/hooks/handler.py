from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict

from ..core.config import load_config
from ..core.events import build_event_from_hook
from ..core.notifier import Notifier

logging.basicConfig(level=logging.INFO)
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


def main() -> int:
    hook_event = os.environ.get("CLAUDE_HOOK_EVENT", "")
    if not hook_event:
        LOGGER.error("缺少 CLAUDE_HOOK_EVENT 环境变量")
        return 1

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}

    try:
        result = process_hook_event(hook_event, payload, os.environ.get("CCNOTIFIER_CONFIG"))
    except Exception as exc:
        LOGGER.exception("处理 hook 事件失败: %s", exc)
        result = {"continue": True}

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

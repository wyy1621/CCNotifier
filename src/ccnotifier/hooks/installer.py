from __future__ import annotations

import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
LOCAL_SETTINGS_PATH = Path.home() / ".claude" / "settings.local.json"
HOOK_TAG = "ccnotifier-managed"


def install_hooks(target: str = "local") -> Path:
    settings_path = _resolve_settings_path(target)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    _backup_file(settings_path)

    settings = _load_json(settings_path)
    hooks = settings.setdefault("hooks", {})

    hooks["Notification"] = _merge_hook_entries(
        hooks.get("Notification", []),
        [_notification_entry()],
    )
    hooks["Stop"] = _merge_hook_entries(
        hooks.get("Stop", []),
        [_stop_entry()],
    )
    hooks["PreToolUse"] = _merge_hook_entries(
        hooks.get("PreToolUse", []),
        [_pre_tool_use_entry()],
    )

    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    return settings_path


def uninstall_hooks(target: str = "local") -> Path:
    settings_path = _resolve_settings_path(target)
    settings = _load_json(settings_path)
    hooks = settings.get("hooks", {})

    for hook_name in ["Notification", "Stop", "PreToolUse"]:
        existing = hooks.get(hook_name, [])
        filtered = [entry for entry in existing if entry.get("_tag") != HOOK_TAG]
        if filtered:
            hooks[hook_name] = filtered
        elif hook_name in hooks:
            del hooks[hook_name]

    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    return settings_path


def build_command() -> str:
    python_executable = str(Path(sys.executable))
    return f'{_quote(python_executable)} -m ccnotifier.hooks.handler'


def _notification_entry() -> Dict[str, Any]:
    return {
        "_tag": HOOK_TAG,
        "matcher": "permission_prompt",
        "hooks": [{"type": "command", "command": build_command()}],
    }


def _stop_entry() -> Dict[str, Any]:
    return {
        "_tag": HOOK_TAG,
        "hooks": [{"type": "command", "command": build_command()}],
    }


def _pre_tool_use_entry() -> Dict[str, Any]:
    return {
        "_tag": HOOK_TAG,
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": build_command()}],
    }


def _merge_hook_entries(existing: List[Dict[str, Any]], new_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    retained = [entry for entry in existing if entry.get("_tag") != HOOK_TAG]
    retained.extend(deepcopy(new_entries))
    return retained


def _resolve_settings_path(target: str) -> Path:
    if target == "global":
        return SETTINGS_PATH
    if target == "local":
        return LOCAL_SETTINGS_PATH
    raise ValueError("target must be 'global' or 'local'")


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    if not isinstance(loaded, dict):
        raise ValueError(f"Settings file must contain a JSON object: {path}")
    return loaded


def _backup_file(path: Path) -> None:
    if not path.exists():
        return
    backup_path = path.with_name(f"{path.name}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(path, backup_path)


def _quote(value: str) -> str:
    if " " in value:
        return f'"{value}"'
    return value

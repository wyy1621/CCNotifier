from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .llm_review import LlmReviewInput

SOURCE = "claude-code-hook"
USER_INTERACTION_EVENT_NAME = "user-interaction-needed"


@dataclass(slots=True)
class NotificationEvent:
    name: str
    source: str
    hook_event: str
    timestamp: int
    session_id: Optional[str]
    cwd: str
    project_name: str
    summary: str
    details: Dict[str, Any]
    raw: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_event_from_hook(hook_event: str, payload: Dict[str, Any]) -> Optional[NotificationEvent]:
    if hook_event == "Notification":
        return _build_notification_event(payload)
    if hook_event == "Stop":
        return _build_stop_event(payload)
    if hook_event == "PreToolUse":
        return _build_pre_tool_use_event(payload)
    return None


# 输入: 原始 hook payload，输出: LLM 命令审核输入；缺少命令时返回 None。
def extract_llm_review_input(payload: Dict[str, Any]) -> Optional[LlmReviewInput]:
    tool_name = _extract_tool_name(payload)
    if tool_name not in {"Bash", "WebFetch"}:
        return None

    command = _extract_review_target(payload, tool_name)
    if not command:
        return None

    cwd = _extract_cwd(payload)
    return LlmReviewInput(
        command=command,
        description=_extract_description(payload),
        cwd=cwd,
        project_name=_project_name(cwd),
    )



def _build_notification_event(payload: Dict[str, Any]) -> Optional[NotificationEvent]:
    notification_type = str(payload.get("type") or payload.get("notification_type") or "")
    if notification_type not in {"permission_prompt", "idle_prompt"}:
        return None

    cwd = _extract_cwd(payload)
    tool_name = _extract_tool_name(payload)
    tool_input_preview = _truncate(_extract_tool_input_preview(payload), 200)
    prompt = str(payload.get("message") or payload.get("prompt") or "")
    summary = "Claude Code 需要你确认权限或提供输入" if notification_type == "permission_prompt" else "Claude Code 正在等待你查看或继续输入"

    return NotificationEvent(
        name=USER_INTERACTION_EVENT_NAME,
        source=SOURCE,
        hook_event="Notification",
        timestamp=int(time.time()),
        session_id=_extract_session_id(payload),
        cwd=cwd,
        project_name=_project_name(cwd),
        summary=summary,
        details={
            "prompt": prompt,
            "tool_name": tool_name,
            "tool_input_preview": tool_input_preview,
            "notification_type": notification_type,
            "session_id": _extract_session_id(payload),
            "cwd": cwd,
        },
        raw=payload,
    )


def _build_stop_event(payload: Dict[str, Any]) -> NotificationEvent:
    cwd = _extract_cwd(payload)
    return NotificationEvent(
        name="claude-stopped",
        source=SOURCE,
        hook_event="Stop",
        timestamp=int(time.time()),
        session_id=_extract_session_id(payload),
        cwd=cwd,
        project_name=_project_name(cwd),
        summary="Claude Code 已停止，等待你查看结果或继续处理",
        details={
            "reason": payload.get("reason", ""),
            "stop_hook_name": payload.get("stop_hook_name", "Stop"),
            "session_id": _extract_session_id(payload),
            "cwd": cwd,
        },
        raw=payload,
    )


def _build_pre_tool_use_event(payload: Dict[str, Any]) -> Optional[NotificationEvent]:
    tool_name = _extract_tool_name(payload)
    if tool_name == "AskUserQuestion":
        return _build_ask_user_question_event(payload)
    return None


def _build_ask_user_question_event(payload: Dict[str, Any]) -> NotificationEvent:
    cwd = _extract_cwd(payload)
    prompt = _extract_ask_user_question_prompt(payload)
    tool_input_preview = _extract_ask_user_question_preview(payload)
    return NotificationEvent(
        name=USER_INTERACTION_EVENT_NAME,
        source=SOURCE,
        hook_event="PreToolUse",
        timestamp=int(time.time()),
        session_id=_extract_session_id(payload),
        cwd=cwd,
        project_name=_project_name(cwd),
        summary="Claude Code 需要你回答问题后继续执行",
        details={
            "prompt": _truncate(prompt, 200),
            "tool_name": "AskUserQuestion",
            "tool_input_preview": _truncate(tool_input_preview, 200),
            "notification_type": "ask_user_question",
            "session_id": _extract_session_id(payload),
            "cwd": cwd,
        },
        raw=payload,
    )


def _extract_session_id(payload: Dict[str, Any]) -> Optional[str]:
    session_id = payload.get("session_id")
    if session_id:
        return str(session_id)
    session = payload.get("session")
    if isinstance(session, dict) and session.get("id"):
        return str(session["id"])
    return None


def _extract_cwd(payload: Dict[str, Any]) -> str:
    cwd = payload.get("cwd") or payload.get("working_directory")
    if isinstance(cwd, str) and cwd:
        return cwd
    return os.getcwd()


def _extract_tool_name(payload: Dict[str, Any]) -> str:
    tool_name = payload.get("tool_name") or payload.get("tool")
    return str(tool_name) if tool_name else ""


def _extract_tool_input_preview(payload: Dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if command:
            return str(command)
        file_path = tool_input.get("file_path") or tool_input.get("path")
        if file_path:
            return str(file_path)
        return str(tool_input)
    if isinstance(tool_input, str):
        return tool_input
    return ""


def _extract_command(payload: Dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        return str(command) if command else ""
    if isinstance(tool_input, str):
        return tool_input
    command = payload.get("command")
    return str(command) if command else ""


def _extract_webfetch_url(payload: Dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        url = tool_input.get("url")
        return str(url) if url else ""
    url = payload.get("url")
    return str(url) if url else ""


def _extract_review_target(payload: Dict[str, Any], tool_name: str) -> str:
    if tool_name == "Bash":
        return _extract_command(payload)
    if tool_name == "WebFetch":
        return _extract_webfetch_url(payload)
    return ""


# 输入: 原始 hook payload，输出: 命令用途说明文本，不存在时返回空字符串。
def _extract_description(payload: Dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for field_name in ("description", "prompt"):
            description = tool_input.get(field_name)
            if description:
                return str(description)
    for field_name in ("description", "prompt"):
        description = payload.get(field_name)
        if description:
            return str(description)
    return ""



def _extract_ask_user_question_prompt(payload: Dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        questions = tool_input.get("questions")
        if isinstance(questions, list):
            for question in questions:
                if isinstance(question, dict):
                    question_text = question.get("question")
                    if isinstance(question_text, str) and question_text.strip():
                        return question_text.strip()

    for field_name in ("message", "prompt"):
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_ask_user_question_preview(payload: Dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""

    questions = tool_input.get("questions")
    if not isinstance(questions, list):
        return ""

    option_labels: list[str] = []
    for question in questions:
        if not isinstance(question, dict):
            continue
        options = question.get("options")
        if not isinstance(options, list):
            continue
        for option in options:
            if not isinstance(option, dict):
                continue
            label = option.get("label")
            if isinstance(label, str) and label.strip():
                option_labels.append(label.strip())
        if option_labels:
            break

    if not option_labels:
        return ""
    return "可选项: " + " / ".join(option_labels[:3])


def _project_name(cwd: str) -> str:
    return Path(cwd).name or cwd


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."

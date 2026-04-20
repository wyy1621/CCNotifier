from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict

from .config import LlmReviewConfig

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "llm_review_system.txt"
CHAT_COMPLETIONS_PATH = "/chat/completions"

LOGGER = logging.getLogger("ccnotifier.core.llm_review")


class LlmReviewDecision(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass(slots=True)
class LlmReviewInput:
    command: str
    description: str
    cwd: str
    project_name: str

    def to_payload(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LlmReviewResult:
    decision: LlmReviewDecision
    reason: str


class LlmReviewError(RuntimeError):
    pass


# 输入: LlmReviewInput，输出: 严格 JSON，包含 decision 和 reason。
def review_command(review_input: LlmReviewInput, config: LlmReviewConfig) -> LlmReviewResult:
    _validate_config(config)
    system_prompt = load_system_prompt()
    payload = {
        "model": config.model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(review_input.to_payload(), ensure_ascii=False)},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    LOGGER.debug("发送给 LLM 的内容: %s", json.dumps(payload, ensure_ascii=False))

    try:
        import requests
    except ImportError as exc:
        raise LlmReviewError("LLM review requires requests") from exc

    response = requests.post(
        _build_chat_completions_url(config.api_base_url),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=config.timeout_seconds,
    )
    if response.status_code != 200:
        raise LlmReviewError(f"LLM review request failed: HTTP {response.status_code}")

    response_data = response.json()
    LOGGER.debug("LLM 原始回复: %s", json.dumps(response_data, ensure_ascii=False))
    content = _extract_response_content(response_data)
    LOGGER.debug("LLM 回复内容: %s", content)
    return _parse_review_result(content)


# 输入: 配置对象，输出: 完整 chat completions URL。
def _build_chat_completions_url(api_base_url: str) -> str:
    return api_base_url.rstrip("/") + CHAT_COMPLETIONS_PATH


# 输入: 配置对象，输出: 无；配置非法时抛异常。
def _validate_config(config: LlmReviewConfig) -> None:
    if not config.enabled:
        raise LlmReviewError("LLM review is disabled")
    if not config.api_base_url:
        raise LlmReviewError("LLM review api_base_url is required")
    if not config.api_key:
        raise LlmReviewError("LLM review api_key is required")
    if not config.model_name:
        raise LlmReviewError("LLM review model_name is required")
    if config.timeout_seconds <= 0:
        raise LlmReviewError("LLM review timeout_seconds must be positive")


# 输入: 无，输出: system prompt 文本。
def load_system_prompt() -> str:
    prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
    if not prompt:
        raise LlmReviewError("LLM review system prompt is empty")
    return prompt


# 输入: OpenAI-compatible 响应 JSON，输出: 模型文本内容。
def _extract_response_content(response_data: Dict[str, Any]) -> str:
    choices = response_data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LlmReviewError("LLM review response missing choices")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise LlmReviewError("LLM review response choice is invalid")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise LlmReviewError("LLM review response missing message")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise LlmReviewError("LLM review response content is empty")
    return content


# 输入: 模型 JSON 文本，输出: LlmReviewResult；格式非法时抛异常。
def _parse_review_result(content: str) -> LlmReviewResult:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LlmReviewError("LLM review response is not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise LlmReviewError("LLM review response must be a JSON object")

    decision = parsed.get("decision")
    reason = parsed.get("reason")
    if decision not in {member.value for member in LlmReviewDecision}:
        raise LlmReviewError("LLM review decision is invalid")
    if not isinstance(reason, str) or not reason.strip():
        raise LlmReviewError("LLM review reason is required")

    return LlmReviewResult(decision=LlmReviewDecision(decision), reason=reason.strip())

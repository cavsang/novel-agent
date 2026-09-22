"""
Editor Agent — STEP 2 최소 버전.

Tool 권한 원칙(STEP 0 §23): Editor -> Draft/Critic 결과 읽기 / Revision Plan 생성.
STEP 10에서 Plot/Character/Continuity/Reader Critic이 추가되면,
Editor는 그 결과들을 종합하는 "Chief Editor" 역할로 확장된다.
지금은 Editor 혼자 Scene Contract 대비 Draft를 검토한다.

반환값은 항상 구조화된 dict (STEP 0 §16/§19 Issue 형식)이며,
단순 점수(예: 7/10)를 반환하지 않는다.
"""

from __future__ import annotations

import json
import logging
import re

from app.core.llm import get_chat_model
from app.prompts.editor import build_editor_prompt

logger = logging.getLogger("novel_agent.editor")


def review_draft(scene_contract: dict, draft: str, revision_count: int) -> dict:
    """
    {"decision": "APPROVE"|"REVISE", "issues": [...]}
    형태의 구조화된 결과를 반환한다. LLM이 JSON 파싱에 실패하면
    안전한 쪽(REVISE)으로 폴백한다 — 검증되지 않은 Draft를 그냥
    통과시키는 것보다는 사람이 볼 수 있게 한 번 더 돌리는 편이
    STEP 0 §2/§20(Quality Gate) 원칙에 부합한다.
    """
    prompt = build_editor_prompt(scene_contract, draft, revision_count)
    model = get_chat_model()
    response = model.invoke(prompt)
    raw = response.content

    parsed = _safe_parse_json(raw)
    if parsed is None:
        logger.warning("editor: JSON 파싱 실패, 안전하게 REVISE로 폴백. raw=%r", raw)
        return {
            "decision": "REVISE",
            "issues": [
                {
                    "severity": "MEDIUM",
                    "type": "other",
                    "problem": "Editor 응답을 구조화된 JSON으로 파싱하지 못함",
                    "suggestion": "Editor 프롬프트/모델 출력 형식을 재확인할 것",
                }
            ],
        }
    return parsed


def _safe_parse_json(raw: str) -> dict | None:
    text = raw.strip()
    # 모델이 ```json ... ``` 로 감싸는 경우 대비
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None

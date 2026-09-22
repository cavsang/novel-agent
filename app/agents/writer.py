"""
Writer Agent.

Tool 권한 원칙(STEP 0 §23): Writer -> Context/Memory 읽기 / Draft 생성.
Writer는 Canonical Story State를 직접 수정하지 않는다 — 이 함수의
반환값은 항상 "Draft" 문자열이며, 그 자체로는 아무것도 커밋하지 않는다.
"""

from __future__ import annotations

from app.core.llm import get_chat_model
from app.prompts.writer import build_writer_prompt


def write_scene(scene_contract: dict, revision_notes: list[dict] | None = None) -> str:
    """Scene Contract(+선택적 revision_notes)를 받아 Draft 문자열을 생성한다."""
    prompt = build_writer_prompt(scene_contract, revision_notes=revision_notes)
    model = get_chat_model()
    response = model.invoke(prompt)
    return response.content

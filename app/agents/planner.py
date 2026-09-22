"""
Chapter / Scene Planner — STEP 2 MVP 버전.

STEP 0 최종 설계에서는 Story Architect가 장기 플롯을 먼저 설계하고
Chapter Planner -> Scene Planner 순으로 내려오지만, STEP 2는
"Planner -> Writer -> Editor -> Revision" 루프 자체를 검증하는 단계이므로
Architect 없이 사용자가 준 premise로 Scene Contract 하나를 직접 만든다.

Story Architect(장기 플롯)와 여러 Scene에 걸친 Chapter 단위 계획은
STEP 3(Story Memory) 이후, 실제 Novel/Chapter 엔티티가 DB에 생기면
그 시점에 추가한다.

Tool 권한 원칙(STEP 0 §23): Planner -> Memory/Todo 읽기 / Plan 생성.
STEP 2에는 아직 Memory/Todo가 없으므로 입력(premise)만으로 생성한다.
"""

from __future__ import annotations

from app.graph.state import NovelState


def build_scene_contract(state: NovelState) -> dict:
    """
    NovelState.scratch["premise"]를 바탕으로 Scene Contract(dict)를 만든다.
    STEP 2에서는 LLM 없이 규칙 기반으로 계약의 뼈대를 채운다 —
    Scene Contract 자체를 LLM에 맡기는 것은 STEP 3 이후 Story Architect가
    장기 플롯 맥락을 함께 줄 수 있을 때가 더 적절하다.
    """
    scratch = state.get("scratch", {}) or {}
    premise: str = scratch.get("premise", "(premise 미지정)")

    return {
        "POV": scratch.get("pov", "주인공 1인칭 근접 3인칭"),
        "Location": scratch.get("location", "(미지정 — premise 기반 추정 필요)"),
        "Time": scratch.get("time", "이야기 시작 시점"),
        "Scene_Goal": scratch.get(
            "scene_goal", f"'{premise}' 전제를 독자에게 자연스럽게 도입한다"
        ),
        "Conflict": scratch.get("conflict", "주인공이 처한 위기 또는 선택의 순간"),
        "Characters": scratch.get("characters", ["주인공"]),
        "What_the_protagonist_knows": scratch.get(
            "protagonist_knows", "자신의 현재 상황과 직면한 위기"
        ),
        "What_the_reader_knows": scratch.get(
            "reader_knows", "주인공 시점에서 드러나는 정보만"
        ),
        "New_Information": scratch.get("new_information", "주인공의 핵심 동기 일부"),
        "Emotional_Arc": scratch.get("emotional_arc", "불안 -> 각성"),
        "World_Building": scratch.get("world_building", "장면에 필요한 최소한만"),
        "Foreshadowing": scratch.get("foreshadowing", "없음 (STEP 8에서 본격 관리)"),
        "Ending_Hook": scratch.get("ending_hook", "다음 장면을 궁금하게 만드는 여운"),
        "Things_That_Must_NOT_Happen": scratch.get(
            "must_not_happen", ["주인공의 진짜 정체/비밀이 이 장면에서 노출되는 것"]
        ),
    }

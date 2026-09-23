"""
Chapter / Scene Planner — STEP 4 버전.

STEP 0 최종 설계에서는 Story Architect가 장기 플롯을 먼저 설계하고
Chapter Planner -> Scene Planner 순으로 내려오지만, Architect는 아직
없으므로(향후 STEP) 사용자가 준 premise로 Scene Contract 하나를 직접
만드는 STEP 2 방식을 유지한다.

STEP 4에서 추가된 것: Tool 권한 원칙(STEP 0 §23) "Planner -> Memory/Todo
읽기 / Plan 생성"을 실제로 구현 — get_active_todos()로 아직 처리되지
않은 Todo를 읽어와 Scene Contract에 "Active_Todos"로 반영한다. 이렇게
하면 예: 이전 Scene에서 심어둔 Foreshadow Todo가 있을 때 Writer가 그걸
인지한 채로 다음 Scene을 쓸 수 있다.
"""

from __future__ import annotations

from app.graph.state import NovelState
from app.memory.repository import get_active_todos


def build_scene_contract(state: NovelState) -> dict:
    """
    NovelState.scratch["premise"]와 Story DB의 활성 Todo를 바탕으로
    Scene Contract(dict)를 만든다.
    """
    scratch = state.scratch
    premise: str = scratch.get("premise", "(premise 미지정)")
    active_todos = get_active_todos(state.novel_id)

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
        "Active_Todos": [t["goal"] for t in active_todos] if active_todos else [],
    }

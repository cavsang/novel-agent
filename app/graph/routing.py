"""
Conditional Routing.

STEP 2 라우팅 포인트 두 곳:
1. orchestrator 이후: PLANNING이면 planner로 진입 (STEP 2에는 task가
   사실상 plan_scene 하나뿐이라 분기가 단순하지만, STEP 3+에서 여러
   task 종류가 생기면 여기서 갈린다)
2. editor 이후: APPROVE -> commit, REVISE(+revision_count < max) ->
   revision, REVISE(+revision_count >= max) -> commit(강제 커밋)

STEP 10 이후에는 editor 이후 라우팅이 Plot/Character/Continuity/Reader
Critic으로 fan-out 되는 형태로 확장될 예정이다.
"""

from __future__ import annotations

from langgraph.graph import END

from app.graph.state import NovelState, RunStatus


def route_after_orchestrator(state: NovelState) -> str:
    status = state.get("status", RunStatus.PENDING)

    if status == RunStatus.PLANNING:
        return "planner"
    return END


def route_after_editor(state: NovelState) -> str:
    status = state.get("status", RunStatus.PENDING)
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 2)

    if status == RunStatus.COMMITTED:
        return "commit"
    if status == RunStatus.REVISING and revision_count < max_revisions:
        return "revision"
    # REVISE인데 revision 한도를 다 썼으면 더 못 고치고 강제 커밋
    # (STEP 13 Human Review로 넘겨야 할 케이스 — 지금은 표식만 남김)
    return "commit"

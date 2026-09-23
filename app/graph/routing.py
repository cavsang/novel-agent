"""
Conditional Routing.

STEP 3부터 NovelState가 Pydantic BaseModel이므로 속성 접근을 사용한다.

라우팅 포인트 두 곳:
1. orchestrator 이후: PLANNING이면 planner로 진입
2. editor 이후: APPROVE -> commit, REVISE(+revision_count < max) ->
   revision, REVISE(+revision_count >= max) -> commit(강제, DB 미저장)
"""

from __future__ import annotations

from langgraph.graph import END

from app.graph.state import NovelState, RunStatus


def route_after_orchestrator(state: NovelState) -> str:
    if state.status == RunStatus.PLANNING:
        return "planner"
    return END


def route_after_editor(state: NovelState) -> str:
    if state.status == RunStatus.COMMITTED:
        return "commit"
    if state.status == RunStatus.REVISING and state.revision_count < state.max_revisions:
        return "revision"
    return "commit"

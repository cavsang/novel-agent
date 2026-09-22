"""
Orchestrator Agent.

Tool 권한 원칙(STEP 0 §23): Orchestrator -> 상태 읽기 / 작업 제어.
STEP 1에서는 graph/nodes.py 안에 stub으로 있었지만, STEP 2부터
실제 Agent 로직이 분리되어 여기로 옮겨졌다. graph/nodes.py는
이제 이 함수를 호출만 하는 얇은 wiring 레이어로 남는다.
"""

from __future__ import annotations

from app.graph.state import RunStatus


def decide_next_task(current_status: RunStatus) -> tuple[RunStatus, str]:
    """
    현재 status를 보고 (다음 status, 다음 task 이름)을 결정한다.

    STEP 2 범위: PENDING -> PLANNING(plan_scene) 하나만 있다.
    STEP 3+에서 여러 task 종류(예: plan_chapter, resume_novel 등)가
    생기면 이 함수가 실제 라우팅 두뇌 역할을 하게 된다.
    """
    if current_status == RunStatus.PENDING:
        return RunStatus.PLANNING, "plan_scene"
    return current_status, "noop"

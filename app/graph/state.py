"""
NovelState — LangGraph가 노드 사이에서 주고받는 실행 상태.

중요: 이 State는 "Canonical Story State"가 아니다.
Canonical Story State(캐릭터/사건/관계 등 정식 소설 세계관 데이터)는
STEP 3에서 PostgreSQL에 별도로 구축한다 (app/memory/models.py 예정).

NovelState는 "지금 이 그래프 실행 한 번"에 대한 임시 작업 상태이며,
LangGraph checkpointer가 여기 담긴 값만 저장/복원한다.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph.message import add_messages


class RunStatus(str, Enum):
    """그래프 실행이 현재 어느 단계에 있는지."""

    PENDING = "pending"
    PLANNING = "planning"
    WRITING = "writing"
    REVIEWING = "reviewing"
    REVISING = "revising"
    COMMITTED = "committed"
    FAILED = "failed"


class NovelState(TypedDict, total=False):
    """
    STEP 2 시점 State.

    STEP 3 이후 아래가 추가될 예정:
      - retrieved_context: list (STEP 5, RAG 결과)
      - critic_reports: list   (STEP 10, Multi-Agent Review — 지금은
        Editor 하나가 issues 리스트로 이를 겸함)
    """

    # ── 그래프 전체 대화/트레이스 메시지 (LangGraph 표준 패턴) ──
    messages: Annotated[list, add_messages]

    # ── 이번 실행이 대상으로 하는 소설/챕터/씬 식별자 ──
    novel_id: str
    current_chapter: Optional[int]
    current_scene: Optional[int]

    # ── Orchestrator가 판단한 현재 작업 ──
    task: str  # 예: "plan_scene", "write_scene", ...
    status: RunStatus

    # ── Planner 산출물 (STEP 2) ──
    scene_contract: Optional[dict]

    # ── Draft / Revision 사이클 (STEP 2) ──
    draft: Optional[str]
    revision_count: int
    max_revisions: int
    revision_notes: Optional[list[dict]]  # Editor가 반환한 구조화된 Issue 목록

    # ── 자유 확장 슬롯 (STEP별로 구조화된 dict가 들어올 자리) ──
    scratch: dict[str, Any]

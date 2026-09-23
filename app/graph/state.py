"""
NovelState — LangGraph가 노드 사이에서 주고받는 실행 상태.

중요: 이 State는 "Canonical Story State"가 아니다.
Canonical Story State(캐릭터/사건/관계 등 정식 소설 세계관 데이터)는
STEP 3부터 PostgreSQL에 별도로 구축한다 (app/memory/models.py).

NovelState는 "지금 이 그래프 실행 한 번"에 대한 임시 작업 상태이며,
LangGraph checkpointer가 여기 담긴 값만 저장/복원한다.

Pydantic BaseModel + Field(description=...)을 사용한다: 모델 자체가
각 필드의 의미를 문서화하고, 나중에 API 응답(app/api)이나 다른 Agent가
이 State를 그대로 참조할 때 스키마 설명이 함께 따라오게 하기 위함이다.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Optional

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """그래프 실행이 현재 어느 단계에 있는지."""

    PENDING = "pending"
    PLANNING = "planning"
    WRITING = "writing"
    REVIEWING = "reviewing"
    REVISING = "revising"
    COMMITTED = "committed"
    FAILED = "failed"


class NovelState(BaseModel):
    """
    STEP 3 시점 State.

    STEP 5 이후 retrieved_context(RAG 결과), STEP 10 이후 critic_reports
    (지금은 Editor 하나가 issues 리스트로 겸함)가 추가될 예정이다.
    """

    messages: Annotated[list, add_messages] = Field(
        default_factory=list,
        description="그래프 실행 전 구간의 트레이스 메시지. LangGraph 표준 add_messages 리듀서로 누적된다.",
    )

    novel_id: str = Field(
        description="이 실행이 대상으로 하는 소설의 식별자. STEP 3부터 Story DB의 Novel.id와 대응한다.",
    )
    current_chapter: Optional[int] = Field(
        default=None, description="현재 작업 중인 Chapter 번호 (1부터 시작). 아직 없으면 None.",
    )
    current_scene: Optional[int] = Field(
        default=None, description="현재 작업 중인 Scene 번호 (Chapter 내 순번). 아직 없으면 None.",
    )

    task: str = Field(
        default="", description="Orchestrator가 판단한 현재 작업 이름. 예: 'plan_scene', 'write_scene'.",
    )
    status: RunStatus = Field(
        default=RunStatus.PENDING, description="그래프 실행의 현재 단계 (RunStatus Enum).",
    )

    scene_contract: Optional[dict] = Field(
        default=None, description="Scene Planner가 생성한 Scene Contract (STEP 0 §11 형식의 dict).",
    )

    draft: Optional[str] = Field(
        default=None, description="Writer/Revision이 생성한 최신 Draft 본문. Canonical Story State가 아니다.",
    )
    revision_count: int = Field(
        default=0, description="현재까지 수행된 Revision 횟수. 0이면 아직 Editor 1차 검토 전이거나 첫 Draft 상태.",
    )
    max_revisions: int = Field(
        default=2, description="허용되는 최대 Revision 횟수. 도달하면 강제 커밋되고 Human Review 대상으로 표시된다 (STEP 13).",
    )
    revision_notes: Optional[list[dict]] = Field(
        default=None, description="Editor가 반환한 구조화된 Issue 목록 (severity/type/problem/suggestion).",
    )

    committed_scene_id: Optional[int] = Field(
        default=None, description="commit_node가 Story DB에 저장한 Scene row의 PK. 저장 성공 시에만 채워진다 (STEP 3).",
    )

    scratch: dict[str, Any] = Field(
        default_factory=dict,
        description="STEP별로 구조화된 dict가 임시로 들어오는 자유 확장 슬롯 (예: STEP 2의 premise 입력).",
    )

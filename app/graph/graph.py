"""
MAIN GRAPH — STEP 2: Planner -> Writer -> Editor -> Revision 루프.

STEP 0의 최종 목표:
    START -> Orchestrator -> Planning Subgraph -> Writing Subgraph
          -> Review Subgraph -> Commit -> END

STEP 2에서는 아직 서브그래프로 나누지 않고, 각 단계를 단일 노드로 둔
"MVP Novel Generation" 파이프라인 하나만 완성한다. STEP 6(Context
Engineering)/STEP 10(Multi-Agent Review) 이후 planning/review 구간이
각각 서브그래프로 승격될 예정이다.
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, START, END

from app.core.config import settings
from app.graph.nodes import (
    commit_node,
    editor_node,
    orchestrator_node,
    planner_node,
    revision_node,
    writer_node,
)
from app.graph.routing import route_after_editor, route_after_orchestrator
from app.graph.state import NovelState

logger = logging.getLogger("novel_agent.graph")


def _build_checkpointer():
    """
    설정된 backend에 따라 checkpointer를 선택한다.

    - memory: 프로세스 메모리에만 저장 (STEP 1 로컬 개발 / 테스트용)
    - postgres: langgraph-checkpoint-postgres 사용, Story DB가
      준비된 이후(STEP 2+)에만 의미가 있다. STEP 1 컨테이너에는
      실제 PostgreSQL이 없으므로 여기서는 배선만 해둔다.
    """
    if settings.checkpointer_backend == "postgres":
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            saver_cm = PostgresSaver.from_conn_string(settings.sqlalchemy_database_url)
            return saver_cm.__enter__()  # 실제 사용 시 context manager로 관리 권장
        except Exception:  # pragma: no cover - STEP 1에서는 DB가 없어 정상적으로 여기로 옴
            logger.warning(
                "postgres checkpointer 연결 실패 — memory checkpointer로 폴백 "
                "(STEP 1에서는 정상, docker compose로 postgres를 띄운 뒤 재시도할 것)"
            )

    from langgraph.checkpoint.memory import MemorySaver

    return MemorySaver()


def build_graph():
    """NovelState 기반 StateGraph를 조립하고 컴파일한다."""
    graph = StateGraph(NovelState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("planner", planner_node)
    graph.add_node("writer", writer_node)
    graph.add_node("editor", editor_node)
    graph.add_node("revision", revision_node)
    graph.add_node("commit", commit_node)

    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {"planner": "planner", END: END},
    )
    graph.add_edge("planner", "writer")
    graph.add_edge("writer", "editor")
    graph.add_conditional_edges(
        "editor",
        route_after_editor,
        {"commit": "commit", "revision": "revision"},
    )
    graph.add_edge("revision", "editor")  # 수정 후 다시 Editor 검토 (Revision Loop)
    graph.add_edge("commit", END)

    checkpointer = _build_checkpointer()
    return graph.compile(checkpointer=checkpointer)


# 모듈 임포트 시 바로 사용할 수 있도록 컴파일된 그래프를 노출
app_graph = build_graph()

"""
그래프 컴파일/체크포인트 최소 Smoke Test.

STEP 2부터 orchestrator 이후 실제 파이프라인(planner->writer->editor
->revision->commit)이 붙었으므로, 여기서는 "그래프가 컴파일되고
실행되며 checkpoint가 상태를 보존하는지"만 최소로 검증한다.
파이프라인 세부 동작 검증은 tests/unit/test_step2_pipeline.py에서 한다.
"""

from app.graph.graph import build_graph
from app.graph.state import RunStatus


def test_graph_compiles():
    graph = build_graph()
    assert graph is not None


def test_graph_runs_to_committed():
    graph = build_graph()
    config = {"configurable": {"thread_id": "test-thread-1"}}

    result = graph.invoke(
        {
            "novel_id": "novel-001",
            "status": RunStatus.PENDING,
            "revision_count": 0,
            "max_revisions": 2,
            "scratch": {},
        },
        config=config,
    )

    assert result["status"] == RunStatus.COMMITTED
    assert len(result["messages"]) > 0


def test_checkpoint_persists_thread_state():
    graph = build_graph()
    config = {"configurable": {"thread_id": "test-thread-2"}}

    graph.invoke(
        {
            "novel_id": "novel-002",
            "status": RunStatus.PENDING,
            "revision_count": 0,
            "max_revisions": 2,
            "scratch": {},
        },
        config=config,
    )

    snapshot = graph.get_state(config)
    assert snapshot.values["status"] == RunStatus.COMMITTED
    assert snapshot.values["novel_id"] == "novel-002"

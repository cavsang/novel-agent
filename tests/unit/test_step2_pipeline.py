"""
STEP 2 실행 검증.

ANTHROPIC_API_KEY가 없는 환경(이 테스트 포함)에서는 MockChatModel이
자동으로 사용된다 — Mock Editor는 revision_count=0일 때 항상 REVISE를
반환하도록 설계되어 있으므로, 이 테스트는 Revision Loop가 실제로
한 번 동작하는 것까지 검증한다.
"""

from app.graph.graph import build_graph
from app.graph.state import RunStatus


def _base_input(novel_id: str) -> dict:
    return {
        "novel_id": novel_id,
        "status": RunStatus.PENDING,
        "revision_count": 0,
        "max_revisions": 2,
        "scratch": {
            "premise": "멸문한 문파의 마지막 제자가 정체를 숨기고 강호로 나선다",
        },
    }


def test_full_pipeline_reaches_committed_after_one_revision():
    graph = build_graph()
    config = {"configurable": {"thread_id": "step2-thread-1"}}

    result = graph.invoke(_base_input("novel-step2-001"), config=config)

    assert result["status"] == RunStatus.COMMITTED
    assert result["scene_contract"] is not None
    assert result["draft"] is not None
    # mock editor: revision_count=0 -> REVISE, revision_count=1 -> APPROVE
    assert result["revision_count"] == 1
    assert result["scratch"]["editor_decision"] == "APPROVE"
    assert result["scratch"]["forced_commit"] is False


def test_pipeline_message_trace_order():
    graph = build_graph()
    config = {"configurable": {"thread_id": "step2-thread-2"}}

    result = graph.invoke(_base_input("novel-step2-002"), config=config)

    roles_and_tags = [m.content.split("]")[0] + "]" for m in result["messages"]]
    # orchestrator -> planner -> writer -> editor(REVISE) -> revision -> editor(APPROVE) -> commit
    assert roles_and_tags == [
        "[orchestrator]",
        "[planner]",
        "[writer]",
        "[editor]",
        "[revision]",
        "[editor]",
        "[commit]",
    ]


def test_scene_contract_has_required_fields():
    graph = build_graph()
    config = {"configurable": {"thread_id": "step2-thread-3"}}

    result = graph.invoke(_base_input("novel-step2-003"), config=config)
    contract = result["scene_contract"]

    for field in [
        "POV",
        "Location",
        "Scene_Goal",
        "Conflict",
        "What_the_reader_knows",
        "Things_That_Must_NOT_Happen",
    ]:
        assert field in contract

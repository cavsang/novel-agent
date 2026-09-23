"""
STEP 3 검증.

SQLite in-memory 치환은 tests/conftest.py의 autouse fixture가
모든 테스트에 공통 적용한다. 여기서는 그 fixture(sqlite_session_factory)를
직접 받아 커밋된 row를 assert하는 데만 사용한다.
"""

from app.graph.graph import build_graph
from app.graph.state import RunStatus
from app.memory.models import Scene
from app.memory.repository import commit_scene


def test_commit_scene_creates_row(sqlite_session_factory):
    session = sqlite_session_factory()
    scene_id = commit_scene(
        novel_id="novel-x",
        chapter_no=1,
        scene_no=1,
        scene_contract={"Scene_Goal": "테스트 목표"},
        draft="테스트 본문",
        session=session,
    )

    saved = session.get(Scene, scene_id)
    assert saved is not None
    assert saved.content == "테스트 본문"


def test_commit_scene_is_idempotent_per_coordinates(sqlite_session_factory):
    session = sqlite_session_factory()
    id1 = commit_scene("novel-x", 1, 1, {"Scene_Goal": "v1"}, "본문 v1", session=session)
    id2 = commit_scene("novel-x", 1, 1, {"Scene_Goal": "v2"}, "본문 v2", session=session)

    assert id1 == id2
    assert session.get(Scene, id2).content == "본문 v2"


def test_full_pipeline_persists_scene_to_story_memory(sqlite_session_factory):
    # commit_node -> repository.commit_scene()이 내부에서 get_session()을
    # 호출한다. tests/conftest.py의 autouse fixture가 이미 SQLite로
    # 치환해뒀으므로 여기서는 별도 monkeypatch가 필요 없다.
    graph = build_graph()
    config = {"configurable": {"thread_id": "step3-thread-1"}}

    result = graph.invoke(
        {
            "novel_id": "novel-step3-001",
            "status": RunStatus.PENDING,
            "scratch": {"premise": "멸문한 문파의 마지막 제자가 정체를 숨기고 강호로 나선다"},
        },
        config=config,
    )

    assert result["status"] == RunStatus.COMMITTED
    assert result["committed_scene_id"] is not None

    session = sqlite_session_factory()
    print(session)
    saved = session.get(Scene, result["committed_scene_id"])
    assert saved is not None
    assert saved.content == result["draft"]
    print(result["draft"])

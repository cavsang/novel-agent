"""
STEP 4 검증: Todo / PlotThread.

tests/conftest.py의 autouse fixture가 SQLite 치환을 담당한다.
"""

from app.graph.graph import build_graph
from app.graph.state import RunStatus
from app.memory.models import PlotThread, Todo
from app.memory.repository import complete_todo, create_todo, get_active_todos


def test_create_todo_and_get_active_todos():
    todo_id = create_todo("novel-todo-1", goal="흑룡문의 존재를 암시할 것", todo_type="foreshadow")

    active = get_active_todos("novel-todo-1")
    assert any(t["id"] == todo_id for t in active)
    assert active[0]["goal"] == "흑룡문의 존재를 암시할 것"


def test_complete_todo_removes_it_from_active_list():
    todo_id = create_todo("novel-todo-2", goal="복선 회수", todo_type="foreshadow")
    complete_todo(todo_id)

    active = get_active_todos("novel-todo-2")
    assert all(t["id"] != todo_id for t in active)


def test_pipeline_creates_plot_thread_and_reads_todo_next_run(sqlite_session_factory):
    graph = build_graph()

    # 1회차: Foreshadowing이 포함된 premise로 실행 -> Todo가 생성돼야 함
    result1 = graph.invoke(
        {
            "novel_id": "novel-step4-001",
            "status": RunStatus.PENDING,
            "scratch": {
                "premise": "멸문한 문파의 마지막 제자가 정체를 숨기고 강호로 나선다",
                "conflict": "정체를 숨긴 주인공과 그를 쫓는 추격자",
                "foreshadowing": "주인공의 검에 새겨진 정체불명의 문양",
            },
        },
        config={"configurable": {"thread_id": "step4-thread-1"}},
    )
    assert result1["status"] == RunStatus.COMMITTED

    session = sqlite_session_factory()
    threads = session.query(PlotThread).all()
    todos = session.query(Todo).filter_by(todo_type="foreshadow").all()
    print(f"todos : {todos}")
    print(f"threads : {threads}")
    assert len(threads) == 1
    assert threads[0].title == "정체를 숨긴 주인공과 그를 쫓는 추격자"
    assert len(todos) == 1
    assert todos[0].goal == "주인공의 검에 새겨진 정체불명의 문양"

    # 2회차: 같은 novel로 다시 실행 -> Planner가 Active_Todos에서 위 Todo를 읽어야 함
    result2 = graph.invoke(
        {
            "novel_id": "novel-step4-001",
            "status": RunStatus.PENDING,
            "scratch": {"premise": "추격자와의 첫 조우"},
        },
        config={"configurable": {"thread_id": "step4-thread-2"}},
    )

    print(f"result2 : {result2}")
    assert "주인공의 검에 새겨진 정체불명의 문양" in result2["scene_contract"]["Active_Todos"]

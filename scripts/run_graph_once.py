"""
python -m scripts.run_graph_once 로 실행.
STEP 2 전체 파이프라인(Planner->Writer->Editor->Revision->Commit)을
한 번 돌려 상태 전이 로그를 눈으로 확인하기 위한 스크립트.
"""

import logging

from app.graph.graph import build_graph
from app.graph.state import RunStatus

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    graph = build_graph()
    config = {"configurable": {"thread_id": "demo-thread"}}

    result = graph.invoke(
        {
            "novel_id": "무림의 마지막 검",
            "status": RunStatus.PENDING,
            "revision_count": 0,
            "max_revisions": 2,
            "scratch": {
                "premise": "멸문한 문파의 마지막 제자가 정체를 숨기고 강호로 나선다",
            },
        },
        config=config,
    )

    print("\n=== FINAL STATE ===")
    print("novel_id:", result["novel_id"])
    print("status:", result["status"])
    print("revision_count:", result["revision_count"])
    print("\n=== SCENE CONTRACT ===")
    for k, v in result["scene_contract"].items():
        print(f"  {k}: {v}")
    print("\n=== FINAL DRAFT ===")
    print(" ", result["draft"])
    print("\n=== MESSAGE TRACE ===")
    for m in result["messages"]:
        content = m.content if hasattr(m, "content") else m["content"]
        print("  -", content)


# if __name__ == "__main__":
#     
main()
"""
LangGraph 노드 wiring 레이어.

이 파일은 실제 로직을 갖지 않는다 — app/agents/*.py, app/memory/repository.py의
함수를 호출해 NovelState를 업데이트하는 얇은 접착부(glue)만 담당한다.

STEP 3부터 NovelState가 Pydantic BaseModel이므로 속성 접근(state.xxx)을
사용한다 (STEP 2까지는 TypedDict라 state["xxx"] / state.get("xxx")였다).
"""

from __future__ import annotations

import logging

from app.agents.editor import review_draft
from app.agents.orchestrator import decide_next_task
from app.agents.planner import build_scene_contract
from app.agents.revision import revise_scene
from app.agents.writer import write_scene
from app.graph.state import NovelState, RunStatus
from app.memory.repository import commit_scene, record_scene_side_effects

logger = logging.getLogger("novel_agent.graph")


def orchestrator_node(state: NovelState) -> dict:
    next_status, task = decide_next_task(state.status)
    logger.info("orchestrator_node: %s -> %s (task=%s)", state.status, next_status, task)

    return {
        "status": next_status,
        "task": task,
        "messages": [{"role": "system", "content": f"[orchestrator] {state.status} -> {next_status} (task={task})"}],
    }


def planner_node(state: NovelState) -> dict:
    contract = build_scene_contract(state)
    logger.info("planner_node: scene contract built (goal=%s)", contract.get("Scene_Goal"))

    return {
        "status": RunStatus.WRITING,
        "scene_contract": contract,
        "revision_count": 0,
        "messages": [{"role": "system", "content": "[planner] scene contract created"}],
    }


def writer_node(state: NovelState) -> dict:
    draft = write_scene(state.scene_contract)
    logger.info("writer_node: draft generated (%d chars)", len(draft))

    return {
        "status": RunStatus.REVIEWING,
        "draft": draft,
        "messages": [{"role": "assistant", "content": f"[writer] draft: {draft[:80]}..."}],
    }


def editor_node(state: NovelState) -> dict:
    result = review_draft(state.scene_contract, state.draft, state.revision_count)
    decision = result.get("decision", "REVISE")
    issues = result.get("issues", [])
    logger.info("editor_node: decision=%s issues=%d", decision, len(issues))

    next_status = RunStatus.COMMITTED if decision == "APPROVE" else RunStatus.REVISING

    return {
        "status": next_status,
        "revision_notes": issues,
        "scratch": {**state.scratch, "editor_decision": decision},
        "messages": [
            {
                "role": "system",
                "content": f"[editor] decision={decision} issues={[i.get('type') for i in issues]}",
            }
        ],
    }


def revision_node(state: NovelState) -> dict:
    revised_draft = revise_scene(state.scene_contract, state.revision_notes or [])
    new_count = state.revision_count + 1
    logger.info("revision_node: revision #%d applied", new_count)

    return {
        "status": RunStatus.REVIEWING,
        "draft": revised_draft,
        "revision_count": new_count,
        "messages": [{"role": "assistant", "content": f"[revision] attempt #{new_count} applied"}],
    }


def commit_node(state: NovelState) -> dict:
    """
    STEP 0 §7 원칙: Validation을 통과한 Draft만 Canonical Story State가 된다.

    STEP 3부터: editor APPROVE인 경우에만 실제로 app/memory/repository를
    통해 PostgreSQL에 Scene을 저장한다. max_revisions 도달로 인한 강제
    커밋은 "검증되지 않은 Draft"이므로 DB에 저장하지 않고, 대신
    revision_notes를 남긴 채 Human Review 대상으로만 표시한다
    (STEP 13에서 실제 Human-in-the-loop 처리 예정).

    STEP 4부터: Scene 저장 성공 시 record_scene_side_effects()를 호출해
    이 Scene의 Conflict를 PlotThread로, Foreshadowing이 있으면 Todo로
    같이 남긴다 (STEP 0 §8/§12).
    """
    forced = (
        state.revision_count >= state.max_revisions
        and state.scratch.get("editor_decision") != "APPROVE"
    )

    if forced:
        note = "[commit] max_revisions 도달, Editor 미승인 — DB 저장 없이 Human Review 대상으로만 표시"
        logger.warning(note)
        return {
            "status": RunStatus.COMMITTED,
            "scratch": {**state.scratch, "forced_commit": True, "needs_human_review": True},
            "messages": [{"role": "system", "content": note}],
        }

    scene_id = commit_scene(
        novel_id=state.novel_id,
        chapter_no=state.current_chapter or 1,
        scene_no=state.current_scene or 1,
        scene_contract=state.scene_contract,
        draft=state.draft,
    )
    side_effects = record_scene_side_effects(
        novel_id=state.novel_id,
        chapter_no=state.current_chapter or 1,
        scene_contract=state.scene_contract,
    )
    note = (
        f"[commit] editor APPROVE — scene_id={scene_id} 로 canonical story state에 저장됨 "
        f"(todo_created={side_effects['created_todo_id']})"
    )
    logger.info(note)

    return {
        "status": RunStatus.COMMITTED,
        "committed_scene_id": scene_id,
        "scratch": {**state.scratch, "forced_commit": False},
        "messages": [{"role": "system", "content": note}],
    }

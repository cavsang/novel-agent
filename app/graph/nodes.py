"""
LangGraph 노드 wiring 레이어.

이 파일은 실제 로직을 갖지 않는다 — app/agents/*.py의 함수를 호출해
NovelState를 업데이트하는 얇은 접착부(glue)만 담당한다.
(Agent 로직과 그래프 배선을 분리해 STEP 3+에서 Agent를 독립적으로
테스트/교체할 수 있게 하기 위함 — STEP 0 §23 Tool 권한 원칙과도 맞음.)
"""

from __future__ import annotations

import logging

from app.agents.editor import review_draft
from app.agents.orchestrator import decide_next_task
from app.agents.planner import build_scene_contract
from app.agents.revision import revise_scene
from app.agents.writer import write_scene
from app.graph.state import NovelState, RunStatus

logger = logging.getLogger("novel_agent.graph")


def orchestrator_node(state: NovelState) -> dict:
    status = state.get("status", RunStatus.PENDING)
    next_status, task = decide_next_task(status)
    logger.info("orchestrator_node: %s -> %s (task=%s)", status, next_status, task)

    return {
        "status": next_status,
        "task": task,
        "messages": [{"role": "system", "content": f"[orchestrator] {status} -> {next_status} (task={task})"}],
    }


def planner_node(state: NovelState) -> dict:
    contract = build_scene_contract(state)
    logger.info("planner_node: scene contract built (goal=%s)", contract.get("Scene_Goal"))

    return {
        "status": RunStatus.WRITING,
        "scene_contract": contract,
        "revision_count": 0,
        "max_revisions": state.get("max_revisions", 2),
        "messages": [{"role": "system", "content": "[planner] scene contract created"}],
    }


def writer_node(state: NovelState) -> dict:
    contract = state["scene_contract"]
    draft = write_scene(contract)
    logger.info("writer_node: draft generated (%d chars)", len(draft))

    return {
        "status": RunStatus.REVIEWING,
        "draft": draft,
        "messages": [{"role": "assistant", "content": f"[writer] draft: {draft[:80]}..."}],
    }


def editor_node(state: NovelState) -> dict:
    contract = state["scene_contract"]
    draft = state["draft"]
    revision_count = state.get("revision_count", 0)

    result = review_draft(contract, draft, revision_count)
    decision = result.get("decision", "REVISE")
    issues = result.get("issues", [])
    logger.info("editor_node: decision=%s issues=%d", decision, len(issues))

    next_status = RunStatus.COMMITTED if decision == "APPROVE" else RunStatus.REVISING

    return {
        "status": next_status,
        "revision_notes": issues,
        "scratch": {**state.get("scratch", {}), "editor_decision": decision},
        "messages": [
            {
                "role": "system",
                "content": f"[editor] decision={decision} issues={[i.get('type') for i in issues]}",
            }
        ],
    }


def revision_node(state: NovelState) -> dict:
    contract = state["scene_contract"]
    issues = state.get("revision_notes") or []
    revised_draft = revise_scene(contract, issues)
    new_count = state.get("revision_count", 0) + 1
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
    STEP 2에는 아직 Story DB(STEP 3)가 없으므로, 여기서는 "커밋 자격을
    얻었다"는 상태 전이만 하고 실제 영속화는 하지 않는다.
    """
    forced = state.get("revision_count", 0) >= state.get("max_revisions", 2) and state.get(
        "scratch", {}
    ).get("editor_decision") != "APPROVE"

    note = (
        "[commit] max_revisions 도달로 강제 커밋 (STEP 13 Human Review 대상으로 표시 필요)"
        if forced
        else "[commit] editor APPROVE — canonical story state 반영 대상 (STEP 3에서 실제 저장 구현)"
    )
    logger.info(note)

    return {
        "status": RunStatus.COMMITTED,
        "scratch": {**state.get("scratch", {}), "forced_commit": forced},
        "messages": [{"role": "system", "content": note}],
    }

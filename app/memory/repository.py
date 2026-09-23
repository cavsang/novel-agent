"""
Story Memory Repository — STEP 0 §22 Write Tools의 최소 구현.

원칙: Agent/Node는 SQLAlchemy Session을 직접 다루지 않는다. 이 모듈이
유일하게 DB 세션을 여닫는 계층이며, 상위 코드(app/graph/nodes.py)는
이 모듈이 제공하는 함수만 호출한다 (STEP 0 §22/§23).

STEP 3 범위: get_or_create_novel, commit_scene.
STEP 4 범위: create_todo, complete_todo, get_active_todos,
get_or_create_plot_thread — STEP 0 §12 Todo 시스템과 §8 PlotThread.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.db.database import get_session
from app.memory.models import Chapter, Novel, PlotThread, Scene, Todo

logger = logging.getLogger("novel_agent.memory")


def get_or_create_novel(session: Session, external_id: str, premise: str | None = None) -> Novel:
    novel = session.query(Novel).filter_by(external_id=external_id).one_or_none()
    if novel is not None:
        return novel

    novel = Novel(external_id=external_id, title=external_id, premise=premise)
    session.add(novel)
    session.flush()  # id 확보
    logger.info("novel created: external_id=%s id=%s", external_id, novel.id)
    return novel


def get_or_create_chapter(session: Session, novel: Novel, chapter_no: int) -> Chapter:
    chapter = (
        session.query(Chapter)
        .filter_by(novel_id=novel.id, chapter_no=chapter_no)
        .one_or_none()
    )
    if chapter is not None:
        return chapter

    chapter = Chapter(novel_id=novel.id, chapter_no=chapter_no)
    session.add(chapter)
    session.flush()
    return chapter


def commit_scene(
    novel_id: str,
    chapter_no: int,
    scene_no: int,
    scene_contract: dict,
    draft: str,
    session: Session | None = None,
) -> int:
    """
    STEP 0 §7 원칙: 여기 호출된다는 것 자체가 "Validation을 통과했다"는
    뜻이다 (commit_node가 Editor APPROVE인 경우에만 이 함수를 부른다).
    Draft를 Scene.content로 저장해 Canonical Story State로 승격시킨다.

    반환값: 저장된 Scene의 PK.
    """
    owns_session = session is None
    session = session or get_session()
    try:
        novel = get_or_create_novel(session, external_id=novel_id, premise=scene_contract.get("premise"))
        chapter = get_or_create_chapter(session, novel, chapter_no)

        scene = (
            session.query(Scene)
            .filter_by(chapter_id=chapter.id, scene_no=scene_no)
            .one_or_none()
        )
        if scene is None:
            scene = Scene(chapter_id=chapter.id, scene_no=scene_no)
            session.add(scene)

        scene.scene_contract_json = json.dumps(scene_contract, ensure_ascii=False)
        scene.content = draft

        session.commit()
        session.refresh(scene)
        return scene.id
    finally:
        if owns_session:
            session.close()


# ── STEP 4: Todo / Plot Thread ──────────────────────────────────────


def get_or_create_plot_thread(
    session: Session, novel: Novel, title: str, summary: str | None = None
) -> PlotThread:
    """
    동일 novel 안에서 title이 같은 PlotThread가 있으면 재사용한다
    (예: Scene Contract의 Conflict 텍스트를 그대로 title로 쓰는 경우,
    같은 갈등이 여러 Scene에 걸쳐 이어질 때 중복 생성을 막기 위함).
    """
    thread = (
        session.query(PlotThread)
        .filter_by(novel_id=novel.id, title=title)
        .one_or_none()
    )
    if thread is not None:
        return thread

    thread = PlotThread(novel_id=novel.id, title=title, summary=summary, status="active")
    session.add(thread)
    session.flush()
    logger.info("plot_thread created: novel_id=%s title=%s", novel.id, title)
    return thread


def create_todo(
    novel_id: str,
    goal: str,
    todo_type: str = "plot",
    priority: str = "normal",
    target_chapter: int | None = None,
    plot_thread_title: str | None = None,
    session: Session | None = None,
) -> int:
    """
    Write Tool: create_todo() (STEP 0 §22).
    plot_thread_title이 주어지면 해당 제목의 PlotThread를 get-or-create
    해서 이 Todo와 연결한다 (없으면 novel-level Todo로만 생성).
    """
    owns_session = session is None
    session = session or get_session()
    try:
        novel = get_or_create_novel(session, external_id=novel_id)

        plot_thread_id = None
        if plot_thread_title:
            thread = get_or_create_plot_thread(session, novel, plot_thread_title)
            plot_thread_id = thread.id

        todo = Todo(
            novel_id=novel.id,
            plot_thread_id=plot_thread_id,
            todo_type=todo_type,
            goal=goal,
            priority=priority,
            target_chapter=target_chapter,
            status="pending",
        )
        session.add(todo)
        session.commit()
        session.refresh(todo)
        logger.info("todo created: id=%s type=%s goal=%s", todo.id, todo_type, goal)
        return todo.id
    finally:
        if owns_session:
            session.close()


def complete_todo(todo_id: int, session: Session | None = None) -> None:
    """Write Tool: complete_todo() (STEP 0 §22)."""
    owns_session = session is None
    session = session or get_session()
    try:
        todo = session.get(Todo, todo_id)
        if todo is None:
            logger.warning("complete_todo: todo_id=%s not found", todo_id)
            return
        todo.status = "done"
        session.commit()
    finally:
        if owns_session:
            session.close()


def record_scene_side_effects(
    novel_id: str, chapter_no: int, scene_contract: dict, session: Session | None = None
) -> dict:
    """
    commit_scene() 성공 직후 호출된다 (commit_node에서). 하나의 세션 안에서
    - Scene Contract의 Conflict를 PlotThread로 get-or-create
    - Foreshadowing이 기본값("없음 ...")이 아니면 그 내용을 Foreshadow Todo로 생성
    을 함께 처리한다. 반환값은 {"plot_thread_id": int|None, "created_todo_id": int|None}.
    """
    owns_session = session is None
    session = session or get_session()
    try:
        novel = get_or_create_novel(session, external_id=novel_id)

        plot_thread_id = None
        conflict = scene_contract.get("Conflict")
        if conflict:
            thread = get_or_create_plot_thread(session, novel, title=conflict)
            plot_thread_id = thread.id

        created_todo_id = None
        foreshadowing = scene_contract.get("Foreshadowing")
        if foreshadowing and not foreshadowing.startswith("없음"):
            todo = Todo(
                novel_id=novel.id,
                plot_thread_id=plot_thread_id,
                todo_type="foreshadow",
                goal=foreshadowing,
                priority="normal",
                target_chapter=None,
                status="pending",
            )
            session.add(todo)
            session.flush()
            created_todo_id = todo.id

        session.commit()
        return {"plot_thread_id": plot_thread_id, "created_todo_id": created_todo_id}
    finally:
        if owns_session:
            session.close()


def get_active_todos(novel_id: str, session: Session | None = None) -> list[dict]:
    """
    Read Tool: get_active_todos() (STEP 0 §22).
    Planner가 다음 Scene Contract를 만들 때 참고할 수 있도록 dict 목록으로
    반환한다 (ORM 객체를 그대로 노출하면 세션이 닫힌 뒤 lazy-load 에러가
    나기 쉬우므로 여기서 값만 뽑아 반환한다).
    """
    owns_session = session is None
    session = session or get_session()
    try:
        novel = session.query(Novel).filter_by(external_id=novel_id).one_or_none()
        if novel is None:
            return []

        todos = (
            session.query(Todo)
            .filter(Todo.novel_id == novel.id, Todo.status.in_(["pending", "active"]))
            .order_by(Todo.priority.desc())
            .all()
        )
        return [
            {
                "id": t.id,
                "todo_type": t.todo_type,
                "goal": t.goal,
                "priority": t.priority,
                "target_chapter": t.target_chapter,
                "status": t.status,
            }
            for t in todos
        ]
    finally:
        if owns_session:
            session.close()

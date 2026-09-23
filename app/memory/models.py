"""
Canonical Story State — SQLAlchemy 모델.

STEP 0 §8 범위: Novel / Character / Chapter / Scene / Todo / PlotThread를
구현한다 (STEP 4에서 Todo/PlotThread 추가). Location, Faction, Item,
Event, Relationship, Foreshadowing(전용 상태 머신), Timeline,
ReaderKnowledge는 §8 계획대로 이후 STEP에서 단계적으로 추가한다.

pgvector 컬럼(임베딩)은 STEP 5(RAG)에서 Scene에 추가할 예정이며,
STEP 3에서는 넣지 않는다 (원칙 8: 필요성 확인 전 기술 추가 금지).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Novel(Base):
    """장편소설 하나. STEP 0 §4 계층 구조의 최상위."""

    __tablename__ = "novels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(
        String(128), unique=True, index=True,
        doc="그래프 실행(NovelState.novel_id)이 참조하는 외부 식별자",
    )
    title: Mapped[str] = mapped_column(String(255))
    premise: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    chapters: Mapped[list["Chapter"]] = relationship(back_populates="novel")
    characters: Mapped[list["Character"]] = relationship(back_populates="novel")
    todos: Mapped[list["Todo"]] = relationship(back_populates="novel")
    plot_threads: Mapped[list["PlotThread"]] = relationship(back_populates="novel")


class Character(Base):
    """STEP 0 §9 CharacterState의 최소 버전. 세부 필드는 STEP 9 이후 확장."""

    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    novel_id: Mapped[int] = mapped_column(ForeignKey("novels.id"))
    name: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    novel: Mapped["Novel"] = relationship(back_populates="characters")


class Chapter(Base):
    """STEP 0 §4 계층: Novel -> (Act/Arc 생략, STEP 3 범위 밖) -> Chapter -> Scene."""

    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    novel_id: Mapped[int] = mapped_column(ForeignKey("novels.id"))
    chapter_no: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    novel: Mapped["Novel"] = relationship(back_populates="chapters")
    scenes: Mapped[list["Scene"]] = relationship(back_populates="chapter")


class Scene(Base):
    """
    Writer가 실제로 집필하는 최소 단위 (STEP 0 §4).
    scene_contract는 STEP 0 §11 형식의 JSON을 텍스트로 직렬화해 저장한다
    (전용 JSON 컬럼 타입은 STEP 4/5에서 쿼리 필요성이 생기면 도입 검토).
    """

    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"))
    scene_no: Mapped[int] = mapped_column(Integer)
    scene_contract_json: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, doc="Editor APPROVE를 통과한 최종 본문")
    committed_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    chapter: Mapped["Chapter"] = relationship(back_populates="scenes")


class PlotThread(Base):
    """
    STEP 0 §8 PlotThread — 여러 Chapter에 걸쳐 이어지는 갈등/사건 축.
    지금은 Scene의 Conflict 필드를 기준으로 Planner/Commit이 만들고
    없어지지 않는 한 계속 active로 남는다. 실제 회수(resolved) 판단
    로직은 STEP 7(Continuity)/STEP 10(Critic) 이후 정교화한다.
    """

    __tablename__ = "plot_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    novel_id: Mapped[int] = mapped_column(ForeignKey("novels.id"))
    title: Mapped[str] = mapped_column(String(255), doc="갈등을 식별하는 짧은 제목 (예: Scene Contract의 Conflict 텍스트)")
    status: Mapped[str] = mapped_column(String(32), default="active", doc="active | resolved | dropped")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    novel: Mapped["Novel"] = relationship(back_populates="plot_threads")
    todos: Mapped[list["Todo"]] = relationship(back_populates="plot_thread")


class Todo(Base):
    """
    STEP 0 §12 Todo 시스템.
    todo_type으로 Plot/Character/World/Foreshadow/Revision/Research를
    구분한다 (§12 "향후 Todo 종류"). plot_thread_id는 이 Todo가 특정
    PlotThread에 종속되는 경우에만 채워진다 (예: 그 갈등의 회수 Todo).
    """

    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    novel_id: Mapped[int] = mapped_column(ForeignKey("novels.id"))
    plot_thread_id: Mapped[int | None] = mapped_column(ForeignKey("plot_threads.id"), nullable=True)
    todo_type: Mapped[str] = mapped_column(String(16), default="plot", doc="plot|character|world|foreshadow|revision|research")
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending", doc="pending|active|done|dropped")
    priority: Mapped[str] = mapped_column(String(16), default="normal", doc="low|normal|high")
    target_chapter: Mapped[int | None] = mapped_column(Integer, nullable=True, doc="이 Todo가 처리되어야 하는 목표 Chapter (미정이면 None)")

    novel: Mapped["Novel"] = relationship(back_populates="todos")
    plot_thread: Mapped["PlotThread"] = relationship(back_populates="todos")

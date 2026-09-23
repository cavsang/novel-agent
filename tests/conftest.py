"""
공통 테스트 fixture.

STEP 3부터 commit_node가 app/memory/repository.commit_scene()을 통해
실제로 DB에 쓴다. 테스트에서 매번 실제 PostgreSQL이 켜져 있을 필요는
없어야 하므로, 모든 테스트에서 자동으로(autouse) SQLite in-memory로
치환한다. 실제 Postgres 연동 자체를 검증하고 싶다면 별도의
integration 테스트(tests/integration/)에서 진짜 DATABASE_URL로 돌린다.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.memory.models import Base


@pytest.fixture()
def sqlite_session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture(autouse=True)
def _patch_story_memory_db(monkeypatch, sqlite_session_factory):
    monkeypatch.setattr("app.memory.repository.get_session", sqlite_session_factory)

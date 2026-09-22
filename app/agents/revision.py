"""
Revision Agent.

STEP 0 §2 원칙: Editor의 Revision Plan(issues)을 받아 Draft를 수정하고,
수정 후 다시 Editor/Validation을 거쳐야 한다. Revision은 별도 Agent로
분리하되 STEP 2에서는 Writer와 동일한 write_scene()을 재사용한다 —
"이전 draft를 참고해 issue를 반영해 다시 쓰기"이므로 근본적으로
Writer의 특수 케이스이기 때문이다. STEP 10 이후 Revision이 더
정교해지면(부분 수정만 하는 diff 기반 편집 등) 이 파일에서 분리한다.
"""

from __future__ import annotations

from app.agents.writer import write_scene


def revise_scene(scene_contract: dict, issues: list[dict]) -> str:
    return write_scene(scene_contract, revision_notes=issues)

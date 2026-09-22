"""
Writer 프롬프트 빌더.

Writer는 Scene Contract를 '계약'으로 받아 이를 지키는 문장을 생성한다.
Writer가 임의로 세계관/설정을 지어내지 않도록, 계약에 없는 정보는
새로 만들지 말라고 명시적으로 지시한다 (STEP 0 §11 원칙).
"""

from __future__ import annotations

SYSTEM_PROMPT = """당신은 장편 무협/판타지 소설의 Scene Writer 입니다.
아래 Scene Contract에 명시된 내용을 반드시 지키며 하나의 Scene을 집필하십시오.

규칙:
- Scene Goal을 달성하는 방향으로 쓸 것
- "Reader가 아는 정보" 범위를 넘어서는 정보를 독자에게 누설하지 말 것
- "Things That Must NOT Happen"에 명시된 사건은 절대 일어나지 않게 할 것
- Scene Contract에 없는 새로운 설정(지명/조직/능력 등)을 임의로 만들지 말 것
- 자연스러운 한국어 소설 문체로 작성할 것
"""


def build_writer_prompt(scene_contract: dict, revision_notes: list[dict] | None = None) -> str:
    contract_text = _format_contract(scene_contract)

    if revision_notes:
        mode = "MODE=REVISION"
        notes_text = "\n".join(
            f"- [{n.get('severity', 'MEDIUM')}] {n.get('type')}: {n.get('problem')} "
            f"(제안: {n.get('suggestion')})"
            for n in revision_notes
        )
        instruction = (
            f"{SYSTEM_PROMPT}\n\n{mode}\n\n"
            f"[Scene Contract]\n{contract_text}\n\n"
            f"[이전 Draft에 대한 Editor 지적사항 — 반드시 반영해서 다시 쓸 것]\n{notes_text}\n"
        )
        return instruction

    mode = "MODE=WRITER"
    return f"{SYSTEM_PROMPT}\n\n{mode}\n\n[Scene Contract]\n{contract_text}\n"


def _format_contract(contract: dict) -> str:
    lines = []
    for key, value in contract.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)

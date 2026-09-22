"""
Editor 프롬프트 빌더.

STEP 0 §16/§19 원칙: Critic/Editor는 점수 하나가 아니라 구조화된
Issue 목록을 반환해야 한다. 여기서는 JSON만 출력하도록 강하게 제약한다.

STEP 2에는 아직 Plot/Character/Continuity Critic이 따로 없으므로
(그건 STEP 10) Editor 하나가 Scene Goal 충족 여부와 "must not happen"
위반 여부만 최소로 검토한다.
"""

from __future__ import annotations

SYSTEM_PROMPT = """당신은 장편 무협/판타지 소설의 Scene Editor 입니다.
주어진 Scene Contract와 Draft를 비교해 검토하십시오.

검토 항목 (STEP 2 최소 범위):
- Scene Goal을 draft가 달성했는가
- "Things That Must NOT Happen"을 위반하지 않았는가
- Reader Knowledge 범위를 벗어난 정보가 노출되지 않았는가

반드시 아래 JSON 형식으로만 답하십시오. 다른 텍스트를 절대 추가하지 마십시오.
{
  "decision": "APPROVE" | "REVISE",
  "issues": [
    {
      "severity": "LOW" | "MEDIUM" | "HIGH",
      "type": "scene_goal" | "forbidden_event" | "reader_knowledge_leak" | "other",
      "problem": "...",
      "suggestion": "..."
    }
  ]
}
issues가 없으면 빈 배열로 답하십시오.
"""


def build_editor_prompt(scene_contract: dict, draft: str, revision_count: int) -> str:
    contract_text = "\n".join(f"{k}: {v}" for k, v in scene_contract.items())
    return (
        f"{SYSTEM_PROMPT}\n\nMODE=EDITOR\nrevision_count={revision_count}\n\n"
        f"[Scene Contract]\n{contract_text}\n\n[Draft]\n{draft}\n"
    )

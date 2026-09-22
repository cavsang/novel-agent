"""
LLM Provider 추상화.

원칙: 특정 LLM 하나에 시스템이 종속되지 않는다 (settings.llm_provider로 전환).

STEP 2에서는 아직 API Key가 없는 환경(CI, 샌드박스)에서도 그래프 구조와
Writer -> Editor -> Revision 루프를 검증할 수 있어야 하므로,
API Key가 없거나 llm_provider="mock"이면 결정론적 MockChatModel로 폴백한다.

실제 문장 품질이 필요한 로컬 개발/운영에서는 .env에 ANTHROPIC_API_KEY 등을
채우면 자동으로 실제 모델을 사용한다.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class LLMResponse:
    content: str


class MockChatModel:
    """
    실제 LLM 없이 노드 로직/그래프 흐름을 검증하기 위한 결정론적 모델.

    동작 규칙 (전부 프롬프트 텍스트 안의 마커를 보고 판단):
    - 프롬프트에 "MODE=WRITER"가 있으면: Scene Contract 요약을 바탕으로
      그럴듯한 형태의 더미 씬 초안을 만든다.
    - 프롬프트에 "MODE=EDITOR"가 있으면: revision_count=0 일 때는 REVISE를,
      그 이후에는 APPROVE를 반환한다 (Revision 루프가 최소 1회 실제로
      동작하는 것을 테스트에서 확인하기 위함).
    """

    def invoke(self, prompt: str) -> LLMResponse:
        if "MODE=EDITOR" in prompt:
            return LLMResponse(content=self._mock_editor_response(prompt))
        if "MODE=REVISION" in prompt:
            return LLMResponse(content=self._mock_draft(prompt, revised=True))
        return LLMResponse(content=self._mock_draft(prompt, revised=False))

    @staticmethod
    def _mock_draft(prompt: str, revised: bool) -> str:
        tag = "REVISED_DRAFT" if revised else "DRAFT"
        digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:8]
        return (
            f"[{tag}:{digest}] (mock) Scene Contract를 반영한 더미 씬 본문입니다. "
            "실제 문장은 ANTHROPIC_API_KEY 설정 후 생성됩니다."
        )

    @staticmethod
    def _mock_editor_response(prompt: str) -> str:
        if "revision_count=0" in prompt:
            return (
                '{"decision": "REVISE", "issues": '
                '[{"severity": "MEDIUM", "type": "scene_goal", '
                '"problem": "(mock) Scene Goal이 draft에서 충분히 드러나지 않음", '
                '"suggestion": "(mock) Scene Goal 관련 행동/대사를 보강할 것"}]}'
            )
        return '{"decision": "APPROVE", "issues": []}'


def get_chat_model():
    """
    settings에 따라 실제 Provider 또는 MockChatModel을 반환한다.

    STEP 2에서는 langchain 통합 호출부(app.core.llm 내부)만 이 함수에
    의존하게 만들어, 나중에 실제 Provider로 교체해도 agents/*.py는
    수정할 필요가 없도록 한다.
    """
    provider = settings.llm_provider
    has_key = {
        "anthropic": bool(settings.anthropic_api_key),
        "openai": bool(settings.openai_api_key),
        "gemini": bool(settings.google_api_key),
    }.get(provider, False)

    if provider == "mock" or not has_key:
        return MockChatModel()

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model="claude-sonnet-4-6", api_key=settings.anthropic_api_key)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model="gpt-4.1", api_key=settings.openai_api_key)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", api_key=settings.google_api_key)

    raise ValueError(f"Unknown llm_provider: {provider}")

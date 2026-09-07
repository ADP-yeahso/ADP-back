"""LLM-backed personalized diary question generation."""

import json
from urllib.request import Request, urlopen

from app.core.config import get_settings


class QuestionGenerator:
    def generate(self, situation_text: str) -> str:
        settings = get_settings()
        if not settings.llm_base_url:
            raise RuntimeError("LLM_BASE_URL is not configured")
        payload = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": "상황을 읽고 작성자가 자신의 감정을 이해하도록 돕는 한국어 질문 하나만 생성하세요."},
                {"role": "user", "content": situation_text},
            ],
            "temperature": 0.7,
            "max_tokens": 120,
        }
        headers = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        request = Request(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
        question = result["choices"][0]["message"]["content"].strip()
        if not question:
            raise RuntimeError("LLM returned an empty question")
        return question
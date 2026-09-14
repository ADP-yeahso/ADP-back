"""Emotion analyzer interface and deterministic local fallback."""

from dataclasses import dataclass
import re

from app.core.config import get_settings


@dataclass(frozen=True)
class EmotionAnalysis:
    primary: str
    secondary: str


class EmotionAnalyzer:
    _keywords: dict[str, tuple[str, ...]] = {
        "anger": ("화", "답답", "짜증", "분노", "억울"),
        "anxiety": ("불안", "걱정", "초조", "긴장", "두려"),
        "sadness": ("슬프", "우울", "지쳤", "힘들", "소진"),
        "guilt": ("미안", "죄책", "내 탓", "자책", "후회"),
        "gratitude": ("감사", "다행", "안도", "고마"),
        "tenderness": ("애틋", "사랑", "소중", "괜찮아", "받아들"),
    }

    def analyze(self, text: str) -> EmotionAnalysis:
        settings = get_settings()
        if settings.emotion_model_base_url:
            return self._analyze_with_custom_model(text, settings.emotion_model_base_url, settings.emotion_model_api_key)
        scores = {
            emotion: sum(len(re.findall(re.escape(keyword), text)) for keyword in keywords)
            for emotion, keywords in self._keywords.items()
        }
        ranked = sorted(scores, key=lambda emotion: (-scores[emotion], emotion))
        if scores[ranked[0]] == 0:
            return EmotionAnalysis("neutral", "gratitude")
        secondary = next((emotion for emotion in ranked[1:] if scores[emotion] > 0), "neutral")
        return EmotionAnalysis(ranked[0], secondary)

    def _analyze_with_custom_model(self, text: str, base_url: str, api_key: str | None) -> EmotionAnalysis:
        import json
        from urllib.request import Request, urlopen

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = Request(
            f"{base_url.rstrip('/')}/predict",
            data=json.dumps({"text": text, "top_k": 2}).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
        predictions = result["predictions"]
        if len(predictions) < 2:
            raise RuntimeError("Custom emotion model must return two predictions")
        return EmotionAnalysis(predictions[0]["emotion"], predictions[1]["emotion"])

"""In-process inference for the team's fine-tuned emotion classifier."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings


@dataclass(frozen=True)
class EmotionAnalysis:
    primary: str
    secondary: str


@lru_cache
def _load_classifier():
    """Load the local Hugging Face checkpoint once for this API process."""
    settings = get_settings()
    model_path = Path(settings.emotion_model_path)
    if not model_path.is_dir():
        raise RuntimeError(f"Emotion model directory does not exist: {model_path}")

    required_files = ("config.json", "model.safetensors", "tokenizer.json")
    missing = [name for name in required_files if not (model_path / name).is_file()]
    if missing:
        raise RuntimeError(f"Emotion model is missing required files: {', '.join(missing)}")

    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(model_path, local_files_only=True)
        model.eval()
    except (ImportError, OSError, ValueError) as exc:
        raise RuntimeError("Emotion model could not be loaded") from exc
    return tokenizer, model


class EmotionAnalyzer:
    def analyze(self, text: str) -> EmotionAnalysis:
        settings = get_settings()
        tokenizer, model = _load_classifier()
        try:
            import torch

            encoded = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            with torch.inference_mode():
                logits = model(**encoded).logits[0]
            top_ids = torch.topk(logits, k=2).indices.tolist()
        except Exception as exc:
            raise RuntimeError("Emotion model failed during inference") from exc

        saved_labels = [
            model.config.id2label.get(int(index), model.config.id2label.get(str(index)))
            for index in top_ids
        ]
        if any(label is None for label in saved_labels):
            raise RuntimeError("Emotion model is missing a label for a predicted class")
        try:
            primary, secondary = (settings.emotion_label_map[label] for label in saved_labels)
        except KeyError as exc:
            raise RuntimeError(
                "EMOTION_LABEL_MAP must map every model label to an application emotion code"
            ) from exc
        return EmotionAnalysis(primary=primary, secondary=secondary)

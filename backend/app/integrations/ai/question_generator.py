"""In-process inference for the team's fine-tuned KoBART question generator."""

from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings


@lru_cache
def _load_model():
    """Load the local KoBART checkpoint once for this API process."""
    settings = get_settings()
    model_path = Path(settings.question_model_path)
    if not model_path.is_dir():
        raise RuntimeError(f"Question model directory does not exist: {model_path}")

    required_files = ("config.json", "generation_config.json", "model.safetensors", "tokenizer.json")
    missing = [name for name in required_files if not (model_path / name).is_file()]
    if missing:
        raise RuntimeError(f"Question model is missing required files: {', '.join(missing)}")

    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_path, local_files_only=True)
        model.eval()
    except (ImportError, OSError, ValueError) as exc:
        raise RuntimeError("Question-generation model could not be loaded") from exc
    return tokenizer, model


class QuestionGenerator:
    def generate(self, situation_text: str) -> str:
        settings = get_settings()
        try:
            import torch

            tokenizer, model = _load_model()
            encoded = tokenizer(situation_text, return_tensors="pt", truncation=True, max_length=512)
            with torch.inference_mode():
                generated = model.generate(
                    **encoded,
                    max_new_tokens=settings.question_max_new_tokens,
                    num_beams=settings.question_num_beams,
                    do_sample=False,
                )
            question = tokenizer.decode(generated[0], skip_special_tokens=True)
        except Exception as exc:
            raise RuntimeError("Custom question-generation model failed during inference") from exc
        if not isinstance(question, str):
            raise RuntimeError("Custom question model must return a string")
        question = question.strip()
        if not question:
            raise RuntimeError("Custom question model returned an empty question")
        return question

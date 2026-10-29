"""In-process inference for the team's fine-tuned emotion classifier.

Where the checkpoint comes from
-------------------------------
* ``EMOTION_MODEL_HF_REPO`` set (MLOps mode): the checkpoint is downloaded from that
  Hugging Face repository.  The revision is ``EMOTION_MODEL_REVISION`` when set,
  otherwise the ``deployed`` row of the Supabase ``model_registry`` table, otherwise
  ``main``.  If the download or load fails, the local checkpoint below is used instead
  so the diary flow keeps working.
* Otherwise: the local checkpoint in ``EMOTION_MODEL_PATH`` (the original behaviour).

Hot swapping
------------
``reload_classifier(revision)`` loads a new revision completely, checks that every
class maps to an application emotion code and that a test inference works, and only
then replaces the model in use.  Requests that are already running finish on the
model they started with.  If anything fails, the current model stays in place.

Input format
------------
Checkpoints produced by the MLOps training kernel contain ``training_info.json`` and
were trained on (situation_text, answer) sentence pairs.  The legacy local checkpoint
was trained on a single text, so it keeps receiving only the answer.
"""

import json
import logging
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

REQUIRED_FILES = ("config.json", "model.safetensors", "tokenizer.json")
LEGACY_MAX_LENGTH = 512


@dataclass(frozen=True)
class EmotionAnalysis:
    primary: str
    secondary: str
    primary_confidence: float | None = None
    secondary_confidence: float | None = None
    model_version: str | None = None


@dataclass(frozen=True)
class _LoadedClassifier:
    tokenizer: Any
    model: Any
    version: str            # "v3" for Hugging Face revisions, "local" for EMOTION_MODEL_PATH
    pair_input: bool        # True: (situation, answer) pairs, False: answer only
    max_length: int
    class_codes: tuple[str, ...]  # application emotion code for each class index


_current: _LoadedClassifier | None = None
_load_lock = threading.Lock()      # first load
_reload_lock = threading.Lock()    # one hot swap at a time


# ---------------------------------------------------------------------------
# Label mapping
# ---------------------------------------------------------------------------
def _resolve_class_codes(id2label: dict, num_labels: int, label_map: dict[str, str]) -> tuple[str, ...]:
    """Map every class index to an application emotion code.

    The saved label name is tried first (for example ``LABEL_4``), then the generic
    ``LABEL_{index}`` key.  The MLOps checkpoints save Korean label names but keep the
    same class order as ``EMOTION_LABEL_MAP``, so the index fallback covers them.
    """
    codes = []
    for index in range(num_labels):
        saved = id2label.get(index, id2label.get(str(index)))
        code = label_map.get(saved) if saved is not None else None
        if code is None:
            code = label_map.get(f"LABEL_{index}")
        if code is None:
            raise RuntimeError(
                f"EMOTION_LABEL_MAP has no entry for class {index} (saved label {saved!r})"
            )
        codes.append(code)
    if len(set(codes)) != len(codes):
        raise RuntimeError("EMOTION_LABEL_MAP maps two classes to the same emotion code")
    return tuple(codes)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def _load_from_dir(model_path: Path, version: str) -> _LoadedClassifier:
    if not model_path.is_dir():
        raise RuntimeError(f"Emotion model directory does not exist: {model_path}")
    missing = [name for name in REQUIRED_FILES if not (model_path / name).is_file()]
    if missing:
        raise RuntimeError(f"Emotion model is missing required files: {', '.join(missing)}")

    pair_input, max_length = False, LEGACY_MAX_LENGTH
    info_file = model_path / "training_info.json"
    if info_file.is_file():
        info = json.loads(info_file.read_text(encoding="utf-8"))
        pair_input, max_length = True, int(info.get("max_len", 256))

    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(model_path, local_files_only=True)
        model.eval()
    except (ImportError, OSError, ValueError) as exc:
        raise RuntimeError("Emotion model could not be loaded") from exc

    settings = get_settings()
    class_codes = _resolve_class_codes(
        model.config.id2label, model.config.num_labels, settings.emotion_label_map
    )
    loaded = _LoadedClassifier(tokenizer, model, version, pair_input, max_length, class_codes)

    # Smoke test so a broken checkpoint is rejected before it serves traffic.
    try:
        with torch.inference_mode():
            logits = model(**_encode(loaded, "오늘 하루를 돌아본다.", "조금 지쳤지만 괜찮다.")).logits
        if logits.shape[-1] != len(class_codes):
            raise RuntimeError("Unexpected number of emotion classes")
    except Exception as exc:
        raise RuntimeError("Emotion model failed its smoke test") from exc
    return loaded


def _deployed_revision() -> str:
    """EMOTION_MODEL_REVISION > model_registry 'deployed' row > 'main'."""
    settings = get_settings()
    if settings.emotion_model_revision:
        return settings.emotion_model_revision
    try:
        from app.db.supabase import get_supabase_client

        client = get_supabase_client()
        if client is not None:
            result = (
                client.table("model_registry").select("hf_revision")
                .eq("status", "deployed").order("version", desc=True).limit(1).execute()
            )
            if result.data and result.data[0].get("hf_revision"):
                return result.data[0]["hf_revision"]
    except Exception:
        logger.exception("Could not read model_registry; falling back to 'main'")
    return "main"


def _download(revision: str) -> Path:
    from huggingface_hub import snapshot_download

    settings = get_settings()
    cache_root = Path(settings.emotion_model_cache_dir)
    target = cache_root / revision.replace("/", "_")
    snapshot_download(
        repo_id=settings.emotion_model_hf_repo,
        revision=revision,
        token=settings.emotion_model_hf_token or None,
        local_dir=target,
    )
    return target


def _load_hf(revision: str) -> _LoadedClassifier:
    return _load_from_dir(_download(revision), revision)


def _load_initial() -> _LoadedClassifier:
    settings = get_settings()
    if settings.emotion_model_hf_repo:
        revision = _deployed_revision()
        try:
            loaded = _load_hf(revision)
            logger.info("Emotion model %s loaded from Hugging Face", revision)
            return loaded
        except Exception:
            logger.exception("Emotion model %s could not be loaded; using local checkpoint", revision)
    return _load_from_dir(Path(settings.emotion_model_path), "local")


def _get_classifier() -> _LoadedClassifier:
    global _current
    if _current is None:
        with _load_lock:
            if _current is None:
                _current = _load_initial()
    return _current


def _prune_cache(keep: set[str]) -> None:
    """Keep the volume small: delete downloaded revisions that are no longer needed."""
    cache_root = Path(get_settings().emotion_model_cache_dir)
    if not cache_root.is_dir():
        return
    for child in cache_root.iterdir():
        if child.is_dir() and child.name not in keep:
            shutil.rmtree(child, ignore_errors=True)


def reload_classifier(revision: str) -> str:
    """Load ``revision`` and swap it in.  Returns the version now in use.

    Raises RuntimeError (and keeps the current model) when the new revision fails.
    """
    global _current
    if not get_settings().emotion_model_hf_repo:
        raise RuntimeError("EMOTION_MODEL_HF_REPO is not configured")
    with _reload_lock:
        previous = _current
        loaded = _load_hf(revision)          # raises before touching _current
        _current = loaded
        keep = {loaded.version.replace("/", "_")}
        if previous is not None and previous.version != "local":
            keep.add(previous.version.replace("/", "_"))   # allow a quick rollback
        _prune_cache(keep)
        logger.info("Emotion model swapped: %s -> %s",
                    previous.version if previous else None, loaded.version)
        return loaded.version


def warm_up_in_background() -> None:
    """Start loading the model without blocking server start-up (MLOps mode only)."""
    if not get_settings().emotion_model_hf_repo:
        return

    def _run() -> None:
        try:
            _get_classifier()
        except Exception:
            logger.exception("Emotion model warm-up failed")

    threading.Thread(target=_run, name="emotion-model-warmup", daemon=True).start()


def current_model_info() -> dict:
    loaded = _current
    if loaded is None:
        return {"loaded": False, "model_version": None}
    return {
        "loaded": True,
        "model_version": loaded.version,
        "pair_input": loaded.pair_input,
        "max_length": loaded.max_length,
    }


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------
def _encode(loaded: _LoadedClassifier, situation_text: str | None, answer_text: str):
    if loaded.pair_input:
        # Must match encode() in the training kernel (train_kernel.py).
        return loaded.tokenizer(
            situation_text or "", answer_text or "",
            return_tensors="pt", truncation="longest_first", max_length=loaded.max_length,
        )
    return loaded.tokenizer(
        answer_text, return_tensors="pt", truncation=True, max_length=loaded.max_length
    )


class EmotionAnalyzer:
    def analyze(self, text: str, situation_text: str | None = None) -> EmotionAnalysis:
        """Classify a diary.

        ``text`` is the answer to the AI question (step 2).  ``situation_text`` (step 1)
        is used by MLOps checkpoints, which were trained on both parts of the diary.
        """
        loaded = _get_classifier()   # this request keeps using this model even if it is swapped
        try:
            import torch

            with torch.inference_mode():
                logits = loaded.model(**_encode(loaded, situation_text, text)).logits[0]
            probabilities = torch.softmax(logits, dim=-1)
            top_ids = torch.topk(logits, k=2).indices.tolist()
        except Exception as exc:
            raise RuntimeError("Emotion model failed during inference") from exc

        primary, secondary = (loaded.class_codes[int(index)] for index in top_ids)
        return EmotionAnalysis(
            primary=primary, secondary=secondary,
            primary_confidence=float(probabilities[top_ids[0]]),
            secondary_confidence=float(probabilities[top_ids[1]]),
            model_version=loaded.version,
        )

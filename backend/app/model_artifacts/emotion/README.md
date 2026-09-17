# Emotion model artifact directory

Mount or place the fine-tuned checkpoint files in this directory:

- `config.json`
- `model.safetensors`
- `tokenizer.json`
- `tokenizer_config.json`

For Railway, the recommended approach is a Volume mounted at `/models/emotion`.
Set `EMOTION_MODEL_PATH=/models/emotion` in Railway Variables and upload these
files to that volume. Do not commit the 487 MB checkpoint to Git.

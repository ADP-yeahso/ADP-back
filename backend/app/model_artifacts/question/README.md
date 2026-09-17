# Question-generation model artifact directory

Mount or place the fine-tuned KoBART checkpoint files in this directory:

- `config.json`
- `generation_config.json`
- `model.safetensors`
- `tokenizer.json`
- `tokenizer_config.json`

For Railway, mount a Volume at `/models/question`, place these files in that
directory, and set `QUESTION_MODEL_PATH=/models/question`. Do not commit the
473 MB checkpoint to Git.

FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \\
    && pip install --no-cache-dir .

COPY app ./app

EXPOSE 8000

# Railway provides PORT at runtime. Keep 8000 as the local-Docker default.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

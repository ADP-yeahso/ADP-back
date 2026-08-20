# ADP

FastAPI backend + Supabase database.

## Repository layout

```text
backend/
	app/                 FastAPI application
	tests/               API tests
	pyproject.toml       Python 3.11 dependencies and tool config
docker-compose.yml     Local API container
```

## Backend setup

Python 3.11 is required. On macOS, install it with Homebrew if needed:

```bash
brew install python@3.11
```

Create the environment and install dependencies:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e 'backend[dev]'
cp backend/.env.example backend/.env
```

Fill in `backend/.env` with the Supabase project URL and service role key. The
service role key is server-only and must never be committed.

Run the API:

```bash
uvicorn app.main:app --app-dir backend --reload
```

The API is available at http://localhost:8000. Health check: `GET /health`.
Interactive API docs: http://localhost:8000/docs.

Run tests:

```bash
pytest backend/tests -q
```

## Docker

After creating `backend/.env`, start the API with:

```bash
docker compose up --build
```

The container listens on port 8000. The deployment target is intentionally not
fixed yet; the Docker image can later be used on EC2 or another container host.
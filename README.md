# ADP

FastAPI backend + Supabase database.

제품 목적과 핵심 기능은 [제품 요구사항 문서](docs/product-spec.md)를 참고하세요.
DB 테이블과 확정된 정책은 [DB 명세서](docs/DB-spec.md)를 참고하세요.

## Repository layout

```text
backend/
	app/                 FastAPI application
	tests/               API tests
	pyproject.toml       Python 3.11 dependencies and tool config
docker-compose.yml     Local API container
supabase/migrations/   Supabase database migrations
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
cd backend
adp-api
```

For development with automatic reload, run this from the repository root:

```bash
uvicorn app.main:app --app-dir backend --reload
```

`SERVER_HOST` and `SERVER_PORT` configure the normal start command. On managed
hosts, `PORT` is accepted automatically when `SERVER_PORT` is not set.

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

## app 하위 폴더 계층 구조
```
app/
├── api/                 # 라우터 및 FastAPI 의존성
│   └── v1/endpoints/    # 도메인별 API 엔드포인트
├── core/                # 설정, 인증·인가, 공통 예외
├── db/                  # Supabase 클라이언트
├── schemas/             # Pydantic 요청·응답 모델
├── services/            # 비즈니스 로직
├── repositories/        # Supabase 데이터 접근
└── integrations/        # 감정 분석 및 Storage 연동
```

## Supabase migration

초기 DB 스키마는 `supabase/migrations/20260820_initial_schema.sql`에 있습니다.
Supabase CLI를 설치하고 프로젝트를 연결한 뒤 개발용 프로젝트에 먼저 적용하세요.

```bash
brew install supabase/tap/supabase
supabase login
supabase link --project-ref <PROJECT_REF>
supabase db push
```

`supabase db push`는 연결된 프로젝트의 스키마를 변경하므로, 운영 프로젝트가 아닌
개발용 프로젝트에서 먼저 RLS와 데이터 접근을 검증해야 합니다.

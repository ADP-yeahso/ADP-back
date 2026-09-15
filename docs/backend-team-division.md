# 백엔드 분업 초안

## 담당 정리

### 승준 - 백엔드 총괄

- 로그인 및 인증
- 사용자·그룹·환자 관련 공통 기능
- 전체 API 구조와 공통 규칙 관리
- DB 마이그레이션 및 Supabase 관리
- 팀원 코드 리뷰와 기능 통합
- Railway 서버 배포 및 운영

담당 파일

- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/api/v1/endpoints/users.py`
- `backend/app/api/v1/endpoints/groups.py`
- `backend/app/api/v1/endpoints/patients.py`
- `backend/app/core/`
- `backend/app/db/`
- `supabase/migrations/`

### 강민 - 돌봄수첩·편지함

- 돌봄수첩 기록 작성·조회·수정·삭제
- 환자 상태, 복약, 병원 방문 관련 기능
- 받은 편지·보낸 편지 구분
- 편지 작성, 수신자 선택, 익명 전송
- 편지 본문 500자 제한
- 읽지 않은 편지 표시와 읽음 처리

담당 파일

- `backend/app/api/v1/endpoints/care_notes.py`
- `backend/app/services/care_notes.py`
- `backend/app/repositories/care_notes.py`
- `backend/app/schemas/care_notes.py`
- 편지함 관련 endpoint/service/repository/schema 파일
- 편지함 DB migration 파일

### 성윤 - 기억·미디어

- 기억 기록 작성·조회·수정·삭제
- 기억 나무 날짜순 조회
- 사진·영상·음성 첨부
- Supabase Storage 연동
- 기억 댓글, 북마크, 좋아요·응원 기능

담당 파일

- `backend/app/api/v1/endpoints/memories.py`
- `backend/app/services/memories.py`
- `backend/app/repositories/memories.py`
- `backend/app/schemas/memories.py`
- `backend/app/api/v1/endpoints/media.py`
- `backend/app/services/media.py`
- `backend/app/repositories/media.py`
- `backend/app/schemas/media.py`
- `backend/app/integrations/storage/supabase_storage.py`

## 같이 맞춰야 하는 부분

- API 요청·응답 형식
- 로그인 사용자 확인 방식
- 그룹 멤버만 기록을 조회할 수 있는 권한 처리
- DB 테이블 및 migration 변경
- 에러 응답 형식
- 테스트 작성 및 프론트 전달용 API 문서

## 작업 방식

1. 각자 담당 파일에서 기능을 개발한다.
2. DB 테이블을 새로 만들거나 수정할 때는 승준에게 먼저 공유한다.
3. 기능 개발 시 관련 API 테스트를 함께 작성한다.
4. PR을 올리면 승준이 공통 구조와 권한 처리를 확인한다.
5. 개발 Supabase에서 테스트한 뒤 Railway에 배포한다.

## Railway 배포

- 서버 배포 담당: 승준
- 배포 전 각 담당자가 담당 기능 테스트 완료
- 환경 변수와 Supabase 키는 Railway Variables에서 관리
- 배포 후 `GET /health`와 주요 API를 확인

## 완료 기준

- 담당 기능의 API 구현 완료
- 관련 schema/service/repository 연결 완료
- 기본 성공·실패 테스트 완료
- 프론트에 요청·응답 형식 공유
- 통합 테스트 후 Railway 배포 확인

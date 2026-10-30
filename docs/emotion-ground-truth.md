# 감정 판정 v2 — 2026-10-04

이 문서는 기존 API/DB 문서의 최종 감정 결정 규칙을 대체합니다.

## 감정 라벨 (2026-10-28 변경)

DB와 API의 상위 감정 ID는 **기존 1–6을 유지하고, 중립만 7에서 0으로 변경**합니다.

| ID | 코드 | 감정 |
| --- | --- | --- |
| 0 | `neutral` | 중립 |
| 1 | `anger` | 분노/답답함 |
| 2 | `anxiety` | 불안/초조 |
| 3 | `sadness` | 슬픔/소진 |
| 4 | `guilt` | 죄책감/자책 |
| 5 | `gratitude` | 감사/안도 |
| 6 | `tenderness` | 애틋함/수용 |

ID `0`을 처리하는 백엔드를 먼저 배포한 뒤, 기존 DB에는
`supabase/migrations/20261028_zero_based_emotion_ids.sql` 전체를 실행합니다.
감정 테이블, 모든 외래 키, 일기·학습 데이터의 감정 ID와 추천 JSON의
감정 ID·태그 부모 ID를 같은 트랜잭션에서 변환합니다. 태그 자체의 ID, 꽃 ID,
추천 순위(`rank=1,2`)와 확률은 보존합니다. 재실행해도 이미 변환된 값은 유지합니다.
앞서 잘못 제공된 전체 ID를 1씩 줄이는 SQL을 실행한 DB도 감정 코드에 맞춰
위 번호로 복구합니다. 원래 DB와 잘못 변환된 DB 모두 같은 파일을 사용합니다.
SQL은 임시 테이블을 사용하지 않는 단일 `DO $emotion_ids$ ... $emotion_ids$;`
블록입니다. SQL Editor에 파일 전체를 붙여넣어 실행하세요.

모델 체크포인트의 `LABEL_0` 등과 DB ID는 별개입니다. `EMOTION_LABEL_MAP`은
학습 당시 클래스 순서에 맞춘 코드 매핑을 유지하며, DB 조회로 0–6 ID를 얻습니다.
ID `0`은 정상 감정이므로 클라이언트도 감정 존재 여부를 `null`과 비교해야 합니다.

## 감정 필드

| 값 | 의미 |
| --- | --- |
| `diaries.final_emotion_id` | AI가 답변에서 분류한 1순위 감정. 추천 저장 시 설정 |
| `diaries.correct_emotion_id` | 선택한 태그 3개의 부모 감정 중 다수결 정답. 태그 저장 시 설정 |
| `diaries.ai_emotion_predictions` | 순위 순서의 JSONB 배열. 감정 2개, 실제 모델 확률, 각 하위 태그 5개 |
| `diary_selected_emotion_tags` | 선택한 하위 태그 3개. 기존 N:M 테이블을 유지하므로 중복 배열 불필요 |
| `diaries.finalized_at` | 최종 저장 완료 시각. 이전 기록은 추정하지 않고 NULL 유지 |
| `diaries.emotion_logic_version` | 기존 기록은 1, 새 추천을 저장한 기록은 2 |

AI 1순위 A, 2순위 B일 때 A 태그 1개 + B 태그 2개를 선택하면:
`final_emotion_id=A`, `correct_emotion_id=B`입니다. 꽃과 기존 `emotion`
응답, 감정 통계는 AI 1순위인 `final_emotion_id`를 사용합니다.
별도 `correct_emotion` 응답으로 사용자 정답의 표시명을 제공합니다.
캘린더에는 완료된 일기만 표시해야 합니다. draft도 AI 감정 ID를 가질 수 있습니다.

## 요청 순서

1. `POST /api/v1/diaries` → 상황 저장
2. `POST /api/v1/diaries/{id}/ai-question` → 질문 생성
3. `PATCH /api/v1/diaries/{id}/answer` → `question_answer_text` 저장
4. `GET /api/v1/diaries/{id}/emotion-tag-suggestions` → 모델 추론 + 추천 스냅샷 저장
5. `PUT /api/v1/diaries/{id}/emotion-tags` → `{"emotion_tag_ids": [11, 21, 22]}`
6. `POST /api/v1/diaries/{id}/finalize` → 완료, 꽃, 학습 샘플을 원자적으로 저장

추천 API는 저장된 답변을 입력으로 사용하며, 같은 답변에 대한 재조회는 저장한
추천을 반환합니다. `rank=1,2`, 실제 softmax `confidence`, `tags`가 반환됩니다.
태그 10개 중 중복 없는 정확히 3개만 선택할 수 있습니다. 추천 없이 태그 저장이나
확정은 불가능합니다. 답변 변경 시 이전 추천·선택·감정을 초기화합니다.
같은 답변 재전송은 추천과 선택을 보존합니다. 상황 변경/질문 재생성 시에도
후속 답변·추천을 초기화합니다. 완료 이후 변경은 막고 finalize 재시도는 멱등입니다.

학습 데이터의 `correct_emotion_id`에는 사용자 다수결 정답,
`ai_predicted_emotion_id`에는 AI 1순위를 기록합니다.
`emotion_training_samples.final_emotion_id`는 기존 학습 코드 호환성을 위해
계속 **사용자 정답**을 담습니다. 새 학습 코드는 명시적인 `correct_emotion_id`를 사용하세요.
기존 완료 일기는 AI 순위를 복구할 수 없으므로 기존 final 값을 유지하고,
그 값을 correct에도 복사합니다. 버전 1의 final을 AI 예측으로 해석하면 안 됩니다.

## 적용 순서

1. Supabase SQL Editor에서 다음 파일 **전체**를 실행합니다:
   `supabase/migrations/20261004_diary_emotion_ground_truth.sql`
2. SQL 성공 후 이 백엔드 브랜치를 배포 브랜치에 병합하고 Railway에 배포합니다.
3. 프런트 변경을 병합하고 앱을 재실행합니다.

Mac에서 SQL 전체 복사:

```sh
pbcopy < supabase/migrations/20261004_diary_emotion_ground_truth.sql
```

psql 사용 환경에서는:

```sh
psql "$ADP_DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/migrations/20261004_diary_emotion_ground_truth.sql
```

컬럼만 추가하면 안 됩니다. 파일에 포함된 RPC 함수와 권한 설정이 모두 필요합니다.
RPC는 service_role만 실행할 수 있으며, 사용자 ID는 인증된 백엔드에서 전달합니다.
운영 DB 적용/배포는 이 변경의 로컬 검증과 GitHub push에 포함되지 않습니다.

확인용 SQL:

```sql
select id, status, emotion_logic_version, final_emotion_id,
       correct_emotion_id, ai_emotion_predictions, finalized_at
from public.diaries order by id desc limit 20;

select diary_id, array_agg(emotion_tag_id order by emotion_tag_id) as selected_tags
from public.diary_selected_emotion_tags group by diary_id order by diary_id desc limit 20;

select diary_id, ai_predicted_emotion_id, correct_emotion_id
from public.emotion_training_samples order by id desc limit 20;
```

## 검증

Python 서비스 회귀 테스트와 별개로 임시 PostgreSQL 16에서 초기 스키마,
새 마이그레이션, `backend/tests/emotion_db_regression.sql`을 순서대로 실행합니다.
`emotion_db_bootstrap.sql`은 로컬 테스트 전용이며 운영 Supabase에서 실행하지 마세요.

0–6 변환 검증은 임시 DB에 bootstrap과 20261012까지의 마이그레이션을 적용한 뒤
다음 명령으로 실행합니다. 기존 데이터 보존, 20261028 마이그레이션 재실행,
ID `0`을 사용하는 추천·선택·최종 확정 RPC를 검증합니다.

```sh
psql "$ADP_TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/tests/emotion_zero_based_db_regression.sql
```

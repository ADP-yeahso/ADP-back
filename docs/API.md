# 마음정원 API 상세 명세 v1.0

> 원본: `API.pdf`  
> Base URL: `/api/v1`  
> 인증: 회원가입·로그인을 제외한 요청에는 `Authorization: Bearer <access_token>`이 필요하다.

공통 실패 응답은 `{ "detail": "오류 메시지" }`이다. `(선택)` 표기가 없는 요청 본문 필드는 필수다.

## 1. 인증 및 사용자

| 기능 | 메서드·경로 | 요청 | 성공 응답 | 주요 실패 |
| --- | --- | --- | --- | --- |
| 회원가입 | `POST /auth/signup` | `email`, `password`, `name`, `phone_number` | `201 { id, email, name }` | 409 중복, 422 입력 오류 |
| 로그인 | `POST /auth/login` | `email`, `password` | `200 { access_token, refresh_token, token_type: "bearer" }` | 401 불일치, 422 입력 오류 |
| 로그아웃 | `POST /auth/logout` | 없음 | `204` | 401 |
| 내 인증 정보 | `GET /auth/me` | 없음 | `200 { id, email, name }` | 401 |
| 프로필 조회 | `GET /users/me` | 없음 | `200 { id, email, name, phone_number, profile_image_url }` | 401 |
| 프로필 수정 | `PATCH /users/me` | `name?`, `phone_number?`, `profile_image_url?` | 프로필 객체 | 409 전화번호 중복, 422 |
| 비밀번호 변경 | `PATCH /users/me/password` | `current_password`, `new_password` | `204` | 400 현재 비밀번호 불일치, 422 |

## 2. 그룹·환자·소통

| 기능 | 메서드·경로 | 요청/파라미터 | 성공 응답 | 주요 실패 |
| --- | --- | --- | --- | --- |
| 그룹 생성 | `POST /groups` | `group_name`, `group_profile_image_url?` | `201 GroupSummary` | 422 |
| 내 그룹 목록 | `GET /groups` | 없음 | `200 GroupSummary[]` | 401 |
| 그룹 참여 | `POST /groups/join` | `invite_code` | `200 GroupSummary` | 404, 422 |
| 그룹 상세 | `GET /groups/{group_id}` | `group_id: integer` | `200 GroupDetail` | 403, 404 |
| 그룹 수정 | `PATCH /groups/{group_id}` | `group_name?`, `group_profile_image_url?` | `200 GroupSummary` | 403, 404, 422 |
| 그룹원 목록 | `GET /groups/{group_id}/members` | `group_id` | `200 GroupMember[]` | 403, 404 |
| 내 호칭·관계 수정 | `PATCH /groups/{group_id}/members/me` | `patients_nickname?`, `patient_relation?` | `200 GroupMember` | 403, 422 |
| 그룹 탈퇴 | `DELETE /groups/{group_id}/members/me` | 없음 | `204` | 403, 409 |
| 응원 보내기 | `POST /groups/{group_id}/members/{user_id}/cheers` | 경로 `group_id`, `user_id` | `201 { id }` | 400, 404, 409 |
| 익명 편지 발송 | `POST /groups/{group_id}/letters` | `receiver_user_id?` (`null`이면 전체), `letter_content` | `201 Letter` | 403, 404, 422 |
| 편지함 조회 | `GET /groups/{group_id}/letters` | 없음 | `200 Letter[]` (발신자 ID 비노출) | 403 |
| 환자 등록 | `POST /groups/{group_id}/patients` | 환자 필드 | `201 Patient` | 403, 409, 422 |
| 환자 상세 | `GET /patients/{patient_id}` | `patient_id` | `200 Patient` | 403, 404 |
| 환자 수정 | `PATCH /patients/{patient_id}` | 환자 필드 모두 선택 | `200 Patient` | 403, 404, 422 |

`GroupSummary = { id, group_name, group_profile_image_url, invite_code, member_count, created_at }`  
`GroupDetail = GroupSummary + { members[] }`  
`GroupMember = { user_id, name, patients_nickname, patient_relation, joined_at }`  
`Patient = { id, patient_name, patient_birth_date, gender, profile_image_url, memo, diagnosis_date, primary_hospital }`

## 3. 감정 일기

| 기능 | 메서드·경로 | 요청/파라미터 | 성공 | 주요 실패 |
| --- | --- | --- | --- | --- |
| 초안 생성 | `POST /diaries` | `group_id`, `situation_text`, `title?`, `record_date?` | `201 Diary(status=draft)` | 403, 422 |
| 목록 | `GET /diaries` | `group_id?`, `page=1`, `size=20` | 본인 일기 `Diary[]` | 403, 422 |
| 상세 | `GET /diaries/{diary_id}` | `diary_id` | `DiaryDetail` | 403, 404 |
| 수정 | `PATCH /diaries/{diary_id}` | `title?`, `situation_text?`, `record_date?` | `Diary` | 403, 404, 409, 422 |
| 삭제 | `DELETE /diaries/{diary_id}` | 없음 | `204` (soft delete) | 403, 404 |
| AI 질문 생성 | `POST /diaries/{diary_id}/ai-question` | 없음 | `{ diary_id, ai_question_text }` | 400, 403, 404 |
| 답변 저장 | `PATCH /diaries/{diary_id}/answer` | `question_answer_text` | `Diary(status=answered)` | 403, 404, 409, 422 |
| 감정 태그 추천 | `GET /diaries/{diary_id}/emotion-tag-suggestions` | 없음 | 상위 3개 감정·태그 | 409, 503 |
| 감정 태그 저장 | `PUT /diaries/{diary_id}/emotion-tags` | `emotion_tag_ids: integer[]` | `Diary(status=tagged)` | 404, 409, 422 |
| 최종 확정 | `POST /diaries/{diary_id}/finalize` | 없음 | `DiaryDetail(status=finalized)` | 404, 409 |
| 감정 통계 | `GET /diaries/analysis` | `period=week|month|six_months|year`, `group_id?` | 기간별 감정 집계 | 403, 422 |

`Diary`는 `id`, `user_id`, `group_id`, `title`, `situation_text`, `ai_question_text`, `question_answer_text`, `final_emotion_id`, `flower_id`, `status`, `record_date`, 생성·수정 시각을 포함한다.

## 4. 기억 기록 (Memory Record)

| 기능 | 메서드·경로 | 요청/파라미터 | 성공 | 주요 실패 |
| --- | --- | --- | --- | --- |
| 생성 | `POST /patients/{patient_id}/memory-records` | `title?`, `context?`, `record_date` | `201 MemoryRecord` | 403, 404, 422 |
| 목록 | `GET /patients/{patient_id}/memory-records` | `page=1`, `size=20`, `from_date?`, `to_date?` | `MemoryRecord[]` | 403, 404, 422 |
| 상세 | `GET /memory-records/{record_id}` | 없음 | `MemoryRecord` | 403, 404 |
| 수정 | `PATCH /memory-records/{record_id}` | `title?`, `context?`, `record_date?` | `MemoryRecord` | 403, 404, 422 |
| 삭제 | `DELETE /memory-records/{record_id}` | 없음 | `204` (soft delete) | 403, 404 |
| 북마크 추가 | `PUT /memory-records/{record_id}/bookmark` | 없음, 멱등 | `{ bookmarked: true }` | 403, 404 |
| 북마크 해제 | `DELETE /memory-records/{record_id}/bookmark` | 없음, 멱등 | `{ bookmarked: false }` | 403, 404 |
| 내 북마크 | `GET /memory-records/bookmarks` | `page=1`, `size=20` | `MemoryRecord[]` | 401, 422 |
| 댓글 작성 | `POST /memory-records/{record_id}/comments` | `comment_text` | `201 Comment` | 403, 404, 422 |
| 댓글 목록 | `GET /memory-records/{record_id}/comments` | 없음 | `Comment[]` | 403, 404 |
| 댓글 삭제 | `DELETE /comments/{comment_id}` | 없음 | `204` (soft delete) | 403, 404 |

`MemoryRecord = { id, patient_id, user_id, title, context, record_date, created_at, media: [], bookmarked: false }`.

## 5. 돌봄수첩

| 기능 | 메서드·경로 | 요청/파라미터 | 성공 |
| --- | --- | --- | --- |
| 오늘 상태 생성 | `POST /patients/{patient_id}/daily-conditions` | 상태 필드와 `record_date` | `201 DailyCondition` |
| 오늘 상태 조회 | `GET /patients/{patient_id}/daily-conditions` | `record_date?` | `DailyCondition[]` |
| 오늘 상태 수정 | `PATCH /patients/{patient_id}/daily-conditions/{condition_id}` | 상태 필드 | `DailyCondition` |
| 행동 기록 생성 | `POST /patients/{patient_id}/behavior-logs` | `behavior_type`, `memo?`, `occurred_at` | `201 BehaviorLog` |
| 행동 기록 목록 | `GET /patients/{patient_id}/behavior-logs` | 없음 | `BehaviorLog[]` |
| 복약 등록 | `POST /patients/{patient_id}/medications` | `medication_name`, `dosage`, `time_of_day`, `start_date`, `note?` | `201 Medication` |
| 복약 목록 | `GET /patients/{patient_id}/medications` | `active_only=false` | `Medication[]` |
| 복약 변경 | `PUT /medications/{medication_id}/change` | 변경 날짜 및 새 약 정보 | 새 `Medication` |
| 복용 상태 upsert | `PUT /medications/{medication_id}/intake-logs/{log_date}` | `status`, `taken_at?` | `IntakeLog` |
| 복용 이력 | `GET /medications/{medication_id}/intake-logs` | 없음 | `IntakeLog[]` |
| 진료 기록 생성 | `POST /patients/{patient_id}/hospital-visits` | 진료 필드 | `201 HospitalVisit` |
| 진료 기록 목록 | `GET /patients/{patient_id}/hospital-visits` | 없음 | `HospitalVisit[]` |
| 진료 기록 상세 | `GET /hospital-visits/{visit_id}` | 없음 | `HospitalVisit` |
| 진료 기록 수정 | `PATCH /hospital-visits/{visit_id}` | 진료 필드 모두 선택 | `HospitalVisit` |

각 돌봄수첩 API는 명세상 403/404를 공통으로 반환하며 입력 검증에는 422를 사용한다. 같은 작성자·날짜의 오늘 상태 중복은 409다.

## 6. 캘린더·정원·미디어

| 기능 | 메서드·경로 | 요청/파라미터 | 성공 |
| --- | --- | --- | --- |
| 월별 캘린더 | `GET /groups/{group_id}/calendar` | `year`, `month` | `{ year, month, days: [{ date, record_count, diary_count, memory_record_count }] }` |
| 날짜 상세 | `GET /groups/{group_id}/calendar/{date}` | `date: YYYY-MM-DD` | `{ date, records: [MemoryRecord] }` |
| 월별 정원 | `GET /gardens` | `year`, `month`, `group_id?` | `{ year, month, flowers, leaf_count }` |
| 업로드 URL 발급 | `POST /media/presign` | `file_name`, `file_type=image|audio|video` | `{ upload_url, file_url, object_path, token }` |
| 미디어 등록 | `POST /groups/{group_id}/gallery` | `file_url`, `file_type`, `duration?`, `sort_order=0`, `diary_id` 또는 `memory_record_id` | `201 Media` |
| 그룹 갤러리 | `GET /groups/{group_id}/gallery` | `page=1`, `size=20` | 최신순 `Media[]` |
| 미디어 삭제 | `DELETE /groups/{group_id}/gallery/{media_id}` | 없음 | `204` |

## Enum 값

| 필드 | 허용값 |
| --- | --- |
| `gender` | `male`, `female`, `other` |
| `meal_status` | `good`, `normal`, `low`, `none` |
| `sleep_status` | `good`, `normal`, `bad` |
| `bowel_status` | `normal`, `changed`, `none` |
| `activity_status` | `normal`, `low`, `high` |
| `mood_status` | `stable`, `anxious`, `irritable`, `depressed`, `other` |
| `cognitive_status` | `normal`, `more_confused`, `memory_decline` |
| `medication_status`, intake `status` | `complete`, `partial`, `missed` |
| `behavior_type` | `repeated_question`, `wandering`, `aggression`, `anxiety`, `sleep_change`, `hallucination`, `meal_refusal`, `fall`, `lost`, `other` |
| `file_type` | `image`, `audio`, `video` |
| `period` | `week`, `month`, `six_months`, `year` |

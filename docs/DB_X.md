# ADP 데이터베이스 명세

> 원본: `DB_X.pdf`  
> 기준: Supabase PostgreSQL

## 공통 원칙

- 인증은 Supabase Auth가 담당하며 `public.users`는 서비스 프로필이다. 비밀번호는 저장하지 않는다.
- `users.id`와 모든 사용자 관련 FK는 `uuid`; 그 밖의 PK/FK는 기본적으로 자동 증가 `integer`다.
- 시각은 `timestamptz`, 날짜만 의미하는 값은 `date`를 쓴다.
- `updated_at`은 PostgreSQL 트리거 `set_updated_at()`으로 갱신한다.
- 그룹 멤버십은 `UNIQUE(user_id, group_id)`이며, 탈퇴 시 행을 삭제한다.
- 모든 테이블에 Supabase RLS를 적용한다. service-role key는 RLS를 우회하므로 API에서도 사용자·그룹 권한을 검증한다.

## 사용자·그룹·환자

### `users`

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | uuid | PK, `auth.users.id` FK |
| `email` | varchar(255) | unique, not null |
| `name` | varchar(255) | not null |
| `phone_number` | varchar(30) | unique, not null |
| `profile_image_url` | varchar(500) | nullable |
| `created_at`, `updated_at` | timestamptz | not null, default now() |

### `groups`

`id`(integer PK), `invite_code`(varchar(100), unique), `group_name`(varchar(255)), `group_profile_image_url`(varchar(500), nullable), `created_at`, `updated_at`을 둔다. 그룹장·역할·상태와 저장된 `members` 컬럼은 없다.

### `group_members`

`id`(integer PK), `user_id`(uuid FK), `group_id`(integer FK), `patients_nickname`(varchar(255)), `patient_relation`(varchar(100))을 둔다. `(user_id, group_id)`는 unique다. 호칭은 환자 이름을 DB 기본값으로 참조하지 않고 가입 시 애플리케이션이 복사한다.

### `patients`

`id`(integer PK), `group_id`(integer FK), `patient_name`(varchar(255)), `patient_birth_date`(date), `gender`(varchar(30) 또는 enum), `profile_image_url`(varchar(500), nullable), `memo`(varchar(1000), nullable), `diagnosis_date`(date, nullable), `primary_hospital`(varchar(255), nullable), `created_at`, `updated_at`을 둔다. 그룹 하나당 환자 한 명을 기준으로 한다.

## 감정 일기

### `diaries`

`id`, `user_id`(uuid FK), `group_id`(integer FK), `title`, `situation_text`, `ai_question_text`, `question_answer_text`, `final_emotion_id`(FK), `flower_id`(FK), `status`(기본 `draft`), `record_date`(timestamptz), 생성·수정·삭제 시각을 둔다. `(user_id, record_date)` 인덱스로 기간 조회를 지원한다.

### 감정 관련 테이블

| 테이블 | 핵심 컬럼·제약 |
| --- | --- |
| `emotions` | `id`, `emotion`(unique), `display_name`; 6개 감정과 중립 1개 |
| `emotion_tags` | `parent_emotion_id` FK, `tag_name`, `display_order`, `is_active` |
| `diary_selected_emotion_tags` | `diary_id`, `emotion_tag_id`; 두 값의 조합 unique |
| `emotion_training_samples` | `diary_id`, `user_id`, `situation_text`, `final_emotion_id`, `created_at`; 최종 선택을 재학습용으로 분리 보관 |
| `flowers` | `emotion_id`, `flower_name`, `sentence` |

사용자는 추천된 두 상위 감정의 하위 태그 10개 중 3개를 선택하고, 두 개 이상 선택된 상위 감정을 최종 감정으로 확정한다.

## 기억 기록·응원

| 테이블 | 핵심 컬럼·제약 |
| --- | --- |
| `memory_records` | `patient_id`, `user_id`, `title?`, `context?`, `record_date`, 생성·수정·삭제 시각; `(patient_id, record_date)` 인덱스 |
| `memory_record_bookmarks` | `user_id`, `memory_record_id`, `created_at`; 조합 unique |
| `memory_record_comments` | `memory_record_id`, `user_id`, `comment_text`, 생성·수정·삭제 시각 |
| `memory_record_reactions` | `memory_record_id`, `user_id`, `reaction_type=like`, `created_at`; 사용자당 기록별 하나(unique) |
| `member_cheers` | `group_id`, `sender_user_id`, `receiver_user_id`, `cheer_date`, `created_at`; 발신자·수신자·날짜 조합 unique |

기억 기록은 `patient_id → patients.group_id`로 그룹을 계산하며 별도 `group_id`는 두지 않는다. 환자의 그룹 멤버 모두가 읽고 쓸 수 있다.

## 돌봄수첩

| 테이블 | 핵심 컬럼 |
| --- | --- |
| `patient_daily_conditions` | `patient_id`, `user_id`, `record_date`, 식사·수면·배변·활동·기분·인지·복약 상태, `behavior_change`, `note?`, 생성·수정 시각 |
| `patient_behavior_logs` | `patient_id`, `user_id`, `behavior_type`, `memo?`, `occurred_at`, `created_at` |
| `medications` | `patient_id`, `medication_name`, `dosage`, `time_of_day`, `start_date`, `end_date?`, `note?`, `is_active`, 생성·수정 시각 |
| `medication_intake_logs` | `medication_id`, `log_date`, `status`, `taken_at?`, 생성·수정 시각; `(medication_id, log_date)` unique |
| `hospital_visits` | `patient_id`, `user_id`, `visit_date`, `hospital_name`, 진료·의료진·복약변경·다음진료·보호자 메모 필드, 생성·수정 시각 |

약 변경 시 기존 약의 `end_date`를 기록하고 `is_active=false`로 전환한 뒤 새 행을 만든다. 오늘 상태는 여러 보호자가 같은 날짜에 각각 작성할 수 있다.

## `media`

`id`, `memory_record_id?`, `diary_id?`, `file_type`, `file_url`, `duration?`, `sort_order`, `created_at`을 둔다. `file_url` 컬럼에는 공개 URL이 아닌 Supabase Storage 경로를 저장한다. 진료 기록 첨부는 현재 범위 밖이다.

## 관계 및 RLS

```text
auth.users 1 ─ 1 public.users
users 1 ─ N group_members N ─ 1 groups
groups 1 ─ 1 patients
patients 1 ─ N memory_records, daily_conditions, behavior_logs,
               medications, hospital_visits
medications 1 ─ N medication_intake_logs
users 1 ─ N diaries N ─ M emotion_tags
diaries N ─ 1 emotions; emotions 1 ─ N flowers
memory_records / diaries 1 ─ N media
```

- 사용자: 본인 프로필만 조회·수정
- 그룹·환자: 해당 그룹 멤버만 접근
- 일기: 작성자 본인만 접근
- 기억 기록·댓글·북마크·반응: 해당 환자 그룹 멤버만 접근
- 돌봄수첩: 해당 환자 그룹 멤버만 접근
- 미디어: 연결된 일기 또는 기억 기록에 접근 가능한 사용자만 접근

## 보류된 결정

- `mood_status`, 행동 유형의 최종 표시 문구·하드코딩 값
- `media.file_type`의 enum 전환 여부
- 감정 통계용 일별 집계 캐시 테이블 도입 여부

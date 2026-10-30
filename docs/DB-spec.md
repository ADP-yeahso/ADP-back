# ADP 데이터베이스 명세

> 감정 필드 및 확정 규칙은 [감정 판정 v2](emotion-ground-truth.md)를 우선 적용합니다.

> 원본 DB 명세서를 기준으로, 확정된 변경사항만 반영한 Supabase PostgreSQL 데이터베이스 명세

## 0. 적용 원칙

### 0.1 인증 및 식별자

- 인증은 Supabase Auth를 사용한다.
- `public.users`는 서비스 프로필 테이블이며, 인증 정보는 `auth.users`가 관리한다.
- `public.users.password`는 저장하지 않는다.
- `public.users.id`는 `auth.users.id`를 참조하는 `uuid` PK다.
- `users`와 연결되는 모든 외래 키(`user_id`, `sender_user_id`, `receiver_user_id`)도 `uuid`다.
- 사용자와 관련되지 않은 PK/FK는 기본적으로 `integer` 자동 증가를 사용한다.

### 0.2 PostgreSQL 공통 규칙

- 시간 정보는 `timestamptz`를 사용한다.
- 날짜만 의미하는 값은 `date`를 사용한다.
- `updated_at`은 PostgreSQL 트리거 함수로 자동 갱신한다.
- 그룹 멤버는 동일 그룹에 중복 가입할 수 없다.
- 그룹 멤버 탈퇴 시 `group_members`에서 해당 행을 삭제한다.
- 회원 탈퇴 시 해당 사용자가 작성한 서비스 기록과 프로필을 삭제하며 복구할 수 없다.
- 모든 테이블은 Supabase RLS를 적용한다.

공통 트리거 함수 예시:

```sql
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## 1. 사용자 및 그룹

### 1.1 `users` - 간병인 및 보호자 프로필

Supabase Auth의 `auth.users`와 1:1로 연결되는 공개 프로필 테이블이다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `uuid` | PK, FK `auth.users.id`, Not Null | Supabase Auth 사용자 ID |
| `email` | `varchar(255)` | Unique, Not Null | 로그인 이메일 또는 프로필 조회용 이메일 |
| `name` | `varchar(255)` | Not Null | 이름 또는 닉네임 |
| `phone_number` | `varchar(30)` | Unique, Not Null | 전화번호 |
| `profile_image_url` | `varchar(500)` | Nullable | 프로필 사진 경로 또는 URL |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 가입 일시 |
| `updated_at` | `timestamptz` | Not Null, Default `now()` | 수정 일시 |

비밀번호는 `public.users`에 저장하지 않는다. 이메일 로그인 비밀번호가 필요한 경우에도 Supabase Auth가 관리한다.

### 1.2 `groups` - 그룹

그룹 하나는 하나의 환자를 기준으로 운영한다. 그룹장 개념이나 역할 구분은 없다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 그룹 ID |
| `invite_code` | `varchar(100)` | Unique, Not Null | 방 참여 코드 |
| `group_name` | `varchar(255)` | Not Null | 그룹 이름 |
| `group_profile_image_url` | `varchar(500)` | Nullable | 그룹 프로필 사진 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 생성 일시 |
| `updated_at` | `timestamptz` | Not Null, Default `now()` | 수정 일시 |

원본의 `members` 컬럼은 저장하지 않는다. 참여 인원은 `group_members`를 집계해 계산한다.

### 1.3 `group_members` - 사용자의 그룹 정보

그룹 초대 링크 또는 초대 코드를 통해 가입한 사용자와 그룹의 연결을 저장한다. 초대 링크를 가진 사용자는 별도 승인 없이 참여할 수 있으며, 모든 멤버는 동일한 권한을 가진다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 고유 식별자 |
| `user_id` | `uuid` | Not Null, FK `users.id` | 연결된 사용자 ID |
| `group_id` | `integer` | Not Null, FK `groups.id` | 연결된 그룹 ID |
| `patients_nickname` | `varchar(255)` | Not Null | 사용자별 환자 호칭 |
| `patient_relation` | `varchar(100)` | Not Null | 환자와의 관계 |

제약 조건:

```sql
UNIQUE (user_id, group_id)
```

`patients_nickname`은 DB 기본값으로 `patients.patient_name`을 참조하지 않는다. 그룹 가입 또는 환자 연결 시 애플리케이션이 환자 이름을 기본값으로 복사하고, 사용자가 자신의 호칭으로 수정할 수 있다.

그룹 탈퇴 시 해당 사용자의 `group_members` 행을 삭제한다. 역할, 가입 상태, 그룹장 관련 컬럼은 두지 않는다. 한 사용자는 여러 그룹에 참여할 수 있으며, 가족이 아닌 친구도 멤버가 될 수 있다.

## 2. 환자

### 2.1 `patients` - 환자

그룹에 연결된 환자 정보다. 그룹 하나당 환자 한 명을 기준으로 한다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 고유 식별자 |
| `group_id` | `integer` | Not Null, FK `groups.id` | 연결된 그룹 ID |
| `patient_name` | `varchar(255)` | Not Null | 환자 이름 |
| `patient_birth_date` | `date` | Not Null | 생년월일 |
| `gender` | `varchar(30)` 또는 PostgreSQL Enum | Not Null | 성별 |
| `profile_image_url` | `varchar(500)` | Nullable | 프로필 사진 경로 또는 URL |
| `memo` | `varchar(1000)` | Nullable | 특이사항 |
| `diagnosis_date` | `date` | Nullable | 치매 진단일, 돌봄수첩 상단 요약용 |
| `primary_hospital` | `varchar(255)` | Nullable | 주 이용 병원, 돌봄수첩 상단 요약용 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 생성 일시 |
| `updated_at` | `timestamptz` | Not Null, Default `now()` | 수정 일시 |

## 3. 감정 일기

### 3.1 `diaries` - 일기 및 꽃

상황 서술부터 감정 선택까지의 전체 플로우를 하나의 테이블에서 관리한다.

```text
상황 서술 -> AI 맞춤 질문 및 답변 -> 감정 자유 서술 -> 감정 묶음 선택
```

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment, Not Null | 일기 고유 식별자 |
| `user_id` | `uuid` | Not Null, FK `users.id` | 작성 사용자 |
| `group_id` | `integer` | Not Null, FK `groups.id` | 소속 그룹 |
| `title` | `varchar(255)` | Nullable | 일기 제목 |
| `situation_text` | `text` | Nullable | 사용자가 자유롭게 쓴 상황 서술 |
| `ai_question_text` | `text` | Nullable | AI가 생성한 맞춤형 질문 |
| `question_answer_text` | `text` | Nullable | 맞춤형 질문에 대한 사용자 답변 및 감정 표현 |
| `final_emotion_id` | `integer` | Nullable, FK `emotions.id` | 최종 확정 감정, 꽃 생성용 |
| `flower_id` | `integer` | Nullable, FK `flowers.id` | 최종 감정에 따라 연결된 꽃 |
| `status` | `varchar(30)` | Not Null, Default `draft` | `draft` 또는 `completed` |
| `record_date` | `timestamptz` | Not Null, Default `now()` | 일기 기록 일시 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 생성 일시 |
| `updated_at` | `timestamptz` | Not Null, Default `now()` | 수정 일시 |
| `deleted_at` | `timestamptz` | Nullable | Soft Delete 일시 |

감정 분석 기간 조회를 위해 다음 인덱스를 둔다.

```sql
CREATE INDEX idx_diaries_user_record_date
ON diaries (user_id, record_date);
```

감정 통계는 `final_emotion_id`와 `record_date`를 기간별로 `GROUP BY`하여 계산한다. 별도의 집계 테이블은 현재 만들지 않는다.

### 3.2 `emotions` - 상위 감정

총 7개를 고정한다. 6개 감정과 중립 감정 1개로 구성한다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Not Null | 고정 감정 라벨 0–6. 매핑은 [감정 판정 v2](emotion-ground-truth.md) 참고 |
| `emotion` | `varchar(50)` | Unique, Not Null | 모델 및 서버에서 사용하는 감정 코드 |
| `display_name` | `varchar(50)` | Not Null | 표시용 감정명 |

상위 감정:

- 분노/답답함
- 불안/초조
- 슬픔/소진
- 죄책감/자책
- 감사/안도
- 애틋함/수용
- 중립

각 감정별 하위 감정 5개는 별도 `emotion_tags`에 저장한다.

### 3.3 `emotion_tags` - 하위 감정 태그

감정 묶음 선택 화면에서 사용하는 하위 감정이다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment, Not Null | 태그 ID |
| `parent_emotion_id` | `integer` | Not Null, FK `emotions.id` | 상위 감정 |
| `tag_name` | `varchar(50)` | Not Null | 하위 감정명 |
| `display_order` | `integer` | Not Null | 표시 순서 |
| `is_active` | `boolean` | Not Null, Default `true` | 사용 여부 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 생성 일시 |

### 3.4 `diary_selected_emotion_tags` - 일기별 선택 감정 태그

일기와 하위 감정 태그의 N:M 매핑 테이블이다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment, Not Null | 고유 식별자 |
| `diary_id` | `integer` | Not Null, FK `diaries.id` | 소속 일기 |
| `emotion_tag_id` | `integer` | Not Null, FK `emotion_tags.id` | 선택된 감정 태그 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 선택 일시 |

중복 선택 방지:

```sql
UNIQUE (diary_id, emotion_tag_id)
```

AI 추천 로직 자체는 저장하지 않는다. 런타임에서 `situation_text`와 `question_answer_text`를 분석하고, 사용자가 선택한 태그 목록을 기준으로 `diaries.final_emotion_id`를 확정한다. 작성 중인 일기는 `status=draft`로 임시 저장하고, 최종 완료 시 `status=completed`로 변경한다.

감정 선택 규칙:

1. AI가 상위 감정 2개를 추천한다.
2. 각 상위 감정의 하위 감정 5개씩, 총 10개를 토글로 표시한다.
3. 사용자는 총 10개 중 3개를 선택한다.
4. 2개 이상 선택된 상위 감정을 최종 감정으로 분류한다.
5. 최종 감정은 `final_emotion_id`에 저장하고, 연결된 꽃을 생성한다.

### 3.5 `emotion_training_samples` - 감정 AI 재학습 데이터

사용자가 직접 선택해 확정한 감정과 당시 상황 서술을 AI 재학습용 데이터로 보존한다. 이 테이블은 서비스용 감정 기록과 분리해 학습 데이터의 수집·검토·재학습 상태를 관리하기 위한 테이블이다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment, Not Null | 학습 데이터 ID |
| `diary_id` | `integer` | Not Null, FK `diaries.id` | 원본 일기 |
| `user_id` | `uuid` | Not Null, FK `users.id` | 라벨을 선택한 사용자 |
| `situation_text` | `text` | Not Null | 사용자가 작성한 상황 서술의 복사본 |
| `final_emotion_id` | `integer` | Not Null, FK `emotions.id` | 사용자가 확정한 최종 감정 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 수집 일시 |

일기 완료 시 서버가 이 테이블에 학습 샘플을 저장한다. 재학습 작업은 운영 데이터와 분리된 별도 작업에서 승인된 샘플만 사용한다.

### 3.6 `flowers` - 꽃 및 색상

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment, Not Null | 꽃 ID |
| `emotion_id` | `integer` | Not Null, FK `emotions.id` | 연결된 감정 |
| `flower_name` | `varchar(100)` | Not Null | 꽃 이름 |
| `sentence` | `varchar(255)` | Not Null | 꽃말 또는 위로 문구 |

매칭 규칙은 감정 7개(중립 포함)와 감정별 꽃 여러 개의 조합이다. 감정별 꽃 개수는 다를 수 있다.

`emotion_content` 테이블은 만들지 않는다. 정적 콘텐츠는 프론트엔드에서 관리한다.

## 4. 나무기록

### 4.1 `memory_records` - 기억 기록

환자에 대한 기억을 그룹 멤버가 함께 열람하는 기록이다. `is_public` 컬럼은 두지 않으며, 해당 환자의 그룹 멤버에게 전체 공개한다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 고유 식별자 |
| `patient_id` | `integer` | Not Null, FK `patients.id` | 연결된 환자 ID |
| `user_id` | `uuid` | Not Null, FK `users.id` | 작성자 |
| `title` | `varchar(255)` | Nullable | 기록 제목 |
| `context` | `text` | Nullable | 텍스트 형태의 기억 |
| `record_date` | `date` | Not Null | 기록 기준 날짜 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 생성 일시 |
| `updated_at` | `timestamptz` | Not Null, Default `now()` | 수정 일시 |
| `deleted_at` | `timestamptz` | Nullable | Soft Delete 일시 |

`group_id`는 이 테이블에 추가하지 않는다. 그룹별 조회는 다음 관계를 사용한다.

```text
memory_records.patient_id -> patients.group_id
```

조회용 인덱스:

```sql
CREATE INDEX idx_memory_records_patient_date
ON memory_records (patient_id, record_date);
```

### 4.2 `memory_record_bookmarks` - 나무기록 북마크

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 고유 식별자 |
| `user_id` | `uuid` | Not Null, FK `users.id` | 북마크한 사용자 |
| `memory_record_id` | `integer` | Not Null, FK `memory_records.id` | 북마크된 기록 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 북마크한 일시 |

```sql
UNIQUE (user_id, memory_record_id)
```

### 4.3 `memory_record_comments` - 나무기록 댓글

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 고유 식별자 |
| `memory_record_id` | `integer` | Not Null, FK `memory_records.id` | 댓글 대상 기록 |
| `user_id` | `uuid` | Not Null, FK `users.id` | 작성자 |
| `comment_text` | `text` | Not Null | 댓글 내용 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 작성 일시 |
| `updated_at` | `timestamptz` | Not Null, Default `now()` | 수정 일시 |
| `deleted_at` | `timestamptz` | Nullable | Soft Delete 일시 |

### 4.4 `memory_record_reactions` - 나무기록 반응

사용자당 기록별 하나의 반응만 허용한다. 반응은 변경하거나 취소할 수 있으며, 현재 정책은 한 게시물당 사용자 한 명당 좋아요 하나다.

권장 기본 컬럼:

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 고유 식별자 |
| `memory_record_id` | `integer` | Not Null, FK `memory_records.id` | 반응 대상 기록 |
| `user_id` | `uuid` | Not Null, FK `users.id` | 반응한 사용자 |
| `reaction_type` | `varchar(30)` | Not Null, Default `like` | 현재 `like`만 사용 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 반응 일시 |

```sql
UNIQUE (memory_record_id, user_id)
```

### 4.5 `member_cheers` - 그룹원 개인 응원

그룹 정보 화면에서 그룹원이 다른 그룹원에게 보내는 응원이다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 고유 식별자 |
| `group_id` | `integer` | Not Null, FK `groups.id` | 응원이 속한 그룹 |
| `sender_user_id` | `uuid` | Not Null, FK `users.id` | 응원을 보낸 사용자 |
| `receiver_user_id` | `uuid` | Not Null, FK `users.id` | 응원 받은 그룹원 |
| `cheer_date` | `date` | Not Null, Default `current_date` | 하루 제한을 적용할 기준 날짜 |
| `cheer_type` | `varchar(50)` | Not Null, Default `encouragement` | 응원 유형 |
| `emoji` | `varchar(20)` | Nullable | 선택한 이모지 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 응원한 일시 |

발신자와 수신자가 모두 해당 그룹의 멤버인지 API와 RLS에서 검증한다. 발신자는 자기 자신을 포함해 여러 그룹원에게 응원을 보낼 수 있다. 동일한 수신자에게는 하루 한 번만 응원할 수 있다. 이모지 또는 응원 유형을 선택할 수 있다.

```sql
UNIQUE (sender_user_id, receiver_user_id, cheer_date)
```

그룹별 응원 기록인 만큼 애플리케이션에서 `group_id`와 두 사용자 모두의 그룹 멤버십도 함께 검증한다.

## 5. 감정 분석 통계

신규 테이블은 만들지 않는다.

1주, 1개월, 6개월, 1년 통계는 다음 컬럼을 기간별로 조회해 계산한다.

```text
diaries.final_emotion_id + diaries.record_date
```

필요한 경우 다음 인덱스를 활용한다.

```sql
CREATE INDEX idx_diaries_emotion_record_date
ON diaries (final_emotion_id, record_date);
```

트래픽 증가 시 `emotion_stats_daily` 집계 캐시 테이블 도입 여부를 별도로 검토한다.

## 6. 돌봄수첩

### 6.1 환자 기본정보 요약

별도 테이블을 만들지 않고 `patients`를 사용한다.

사용 컬럼:

```text
patient_name
patient_birth_date
diagnosis_date
primary_hospital
```

수정은 `patients UPDATE`로 처리한다.

### 6.2 `patient_daily_conditions` - 오늘의 환자 상태

여러 보호자가 같은 날 각각 기록할 수 있도록 `patient_id` 단독 Unique 제약은 두지 않는다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 고유 식별자 |
| `patient_id` | `integer` | Not Null, FK `patients.id` | 대상 환자 |
| `user_id` | `uuid` | Not Null, FK `users.id` | 작성자 |
| `record_date` | `date` | Not Null | 기록 날짜 |
| `meal_status` | `varchar(20)` | Not Null, CHECK | 식사: 좋음/보통/적음/거의 못함 |
| `sleep_status` | `varchar(20)` | Not Null, CHECK | 수면: 좋음/보통/나쁨 |
| `bowel_status` | `varchar(20)` | Not Null, CHECK | 배변: 정상/변화 있음/없음 |
| `activity_status` | `varchar(20)` | Not Null, CHECK | 활동·운동: 평소와 비슷/적음/많음 |
| `mood_status` | `varchar(20)` | Not Null | 기분·정서 상태, 최종 값 미정 |
| `cognitive_status` | `varchar(30)` | Not Null, CHECK | 인지: 평소와 비슷/혼란 증가/기억력 저하 체감 |
| `behavior_change` | `boolean` | Not Null, Default `false` | 행동 변화 유무 |
| `medication_status` | `varchar(20)` | Not Null, CHECK | 복약: 완료/일부 누락/미복용 |
| `note` | `text` | Nullable | 오늘의 특이사항 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 생성 일시 |
| `updated_at` | `timestamptz` | Not Null, Default `now()` | 수정 일시 |

조회용 인덱스:

```sql
CREATE INDEX idx_daily_conditions_patient_date
ON patient_daily_conditions (patient_id, record_date);
```

여러 보호자가 같은 날 각각 한 건씩 작성할 수 있다. 보호자별 하루 한 건 제한은 두지 않는다.

### 6.3 `patient_behavior_logs` - 행동 및 증상 기록

하루에 여러 번 발생할 수 있으므로 `patient_daily_conditions`와 분리한다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 고유 식별자 |
| `patient_id` | `integer` | Not Null, FK `patients.id` | 대상 환자 |
| `user_id` | `uuid` | Not Null, FK `users.id` | 작성자 |
| `behavior_type` | `varchar(30)` | Not Null, CHECK | 행동 유형, 최종 값 미정 |
| `memo` | `text` | Nullable | 상세 메모 |
| `occurred_at` | `timestamptz` | Not Null | 발생 시각 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 생성 일시 |

### 6.4 `medications` - 복약 목록

약이 변경되면 기존 행을 종료하고 새 행을 추가해 이력을 관리한다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 고유 식별자 |
| `patient_id` | `integer` | Not Null, FK `patients.id` | 대상 환자 |
| `medication_name` | `varchar(255)` | Not Null | 약 이름 |
| `dosage` | `varchar(100)` | Not Null | 복용량 |
| `time_of_day` | `varchar(100)` | Not Null | 복용 시간, 예: 아침/저녁 또는 08:00 |
| `start_date` | `date` | Not Null | 복용 시작일 |
| `end_date` | `date` | Nullable | 복용 종료 또는 변경일 |
| `note` | `text` | Nullable | 약 변경 후 특이사항 |
| `is_active` | `boolean` | Not Null, Default `true` | 현재 복용 중 여부 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 생성 일시 |
| `updated_at` | `timestamptz` | Not Null, Default `now()` | 수정 일시 |

약 변경 처리:

```text
기존 행 end_date 기록 및 is_active=false
-> 새 약 행 추가
```

### 6.5 `medication_intake_logs` - 일별 복용 여부

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 고유 식별자 |
| `medication_id` | `integer` | Not Null, FK `medications.id` | 대상 약 |
| `log_date` | `date` | Not Null | 복용 확인 날짜 |
| `status` | `varchar(20)` | Not Null, CHECK | 복용 여부: 완료/일부 누락/미복용 |
| `taken_at` | `timestamptz` | Nullable | 실제 복용 시각 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 생성 일시 |
| `updated_at` | `timestamptz` | Not Null, Default `now()` | 수정 일시 |

```sql
UNIQUE (medication_id, log_date)
```

### 6.6 `hospital_visits` - 병원 및 진료 기록

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 고유 식별자 |
| `patient_id` | `integer` | Not Null, FK `patients.id` | 대상 환자 |
| `user_id` | `uuid` | Not Null, FK `users.id` | 작성자 |
| `visit_date` | `date` | Not Null | 방문 날짜 |
| `hospital_name` | `varchar(255)` | Not Null | 병원명 |
| `department` | `varchar(100)` | Nullable | 진료과 |
| `visit_reason` | `text` | Nullable | 방문 이유 |
| `message_to_doctor` | `text` | Nullable | 의료진에게 전달한 내용 |
| `doctor_instructions` | `text` | Nullable | 의료진 안내사항 |
| `medication_changed` | `boolean` | Not Null, Default `false` | 약 변경 여부 |
| `next_visit_date` | `date` | Nullable | 다음 진료일 |
| `guardian_memo` | `text` | Nullable | 보호자 메모 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 생성 일시 |
| `updated_at` | `timestamptz` | Not Null, Default `now()` | 수정 일시 |

## 7. 첨부파일

### 7.1 `media` - 첨부파일 메타데이터

기억 기록과 감정 일기에 연결되는 첨부파일 메타데이터다. 돌봄수첩의 진료 기록 첨부는 현재 범위에 포함하지 않는다.

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK, Auto Increment | 고유 식별자 |
| `memory_record_id` | `integer` | Nullable, FK `memory_records.id` | 연결된 나무기록 |
| `diary_id` | `integer` | Nullable, FK `diaries.id` | 연결된 일기 |
| `file_type` | `varchar(500)` | Not Null | 파일 타입 |
| `file_url` | `varchar(500)` | Not Null | 컬럼명은 유지하지만 실제 값은 Supabase Storage 경로 |
| `duration` | `integer` | Nullable | 영상 또는 음성 재생 시간 |
| `sort_order` | `smallint` | Not Null, Default `0` | 첨부 표시 순서 |
| `created_at` | `timestamptz` | Not Null, Default `now()` | 생성 일시 |

`file_url`에는 공개 URL을 저장하지 않고 Storage의 `storage_path` 값을 저장한다. URL이 필요한 경우 API에서 Storage 경로를 이용해 생성한다.

진료 기록 사진이나 처방전 첨부가 필요해지면 향후 `hospital_visit_id` FK를 추가한다.

## 8. 관계 요약

```text
auth.users 1 --- 1 public.users
public.users 1 --- N group_members N --- 1 groups
 groups 1 --- 1 patients
 patients 1 --- N memory_records
 patients 1 --- N patient_daily_conditions
 patients 1 --- N patient_behavior_logs
 patients 1 --- N medications 1 --- N medication_intake_logs
 patients 1 --- N hospital_visits
 users 1 --- N diaries N --- M emotion_tags
 diaries N --- 1 emotions
 emotions 1 --- N flowers
 memory_records 1 --- N media
 diaries 1 --- N media
 memory_records 1 --- N comments / bookmarks / reactions
 groups 1 --- N member_cheers
```

## 9. 접근 제어 및 RLS 원칙

- `users`: 본인 프로필만 조회 및 수정한다.
- `groups`: 그룹 멤버만 조회한다.
- `group_members`: 본인이 참여한 그룹의 멤버 정보를 조회한다.
- `patients`: 해당 그룹의 멤버만 조회 및 작성한다.
- `diaries`: 작성자 본인만 조회 및 수정한다.
- `memory_records`: 해당 환자 그룹의 멤버만 조회 및 작성한다.
- `memory_record_comments`, `memory_record_bookmarks`, `memory_record_reactions`: 해당 기억 기록의 그룹 멤버만 접근한다.
- `member_cheers`: 발신자와 수신자가 모두 해당 그룹의 멤버인지 검증한다.
- `patient_daily_conditions`, `patient_behavior_logs`, `medications`, `medication_intake_logs`, `hospital_visits`: 해당 환자 그룹의 멤버만 접근한다.
- `media`: 연결된 일기 또는 기억 기록에 접근할 수 있는 사용자만 접근한다.
- Supabase `service_role_key`는 RLS를 우회하므로 FastAPI API 계층에서 현재 사용자 UUID와 그룹 멤버십을 추가로 검증한다.

## 10. 원본 설계에서 보류된 결정

다음 항목은 원본 문서와 동일하게 아직 확정하지 않는다.

- `mood_status`와 행동 유형의 최종 표시 문구 및 하드코딩 값 목록
- `media.file_type`을 ENUM으로 전환할지 여부
- 감정분석 트래픽 증가 시 `emotion_stats_daily` 집계 캐시 테이블 도입 여부

## 11. 원본 대비 반영된 변경사항 요약

| 구분 | 원본 | 적용 명세 |
| --- | --- | --- |
| 인증 | `users.password` 저장 | 삭제, Supabase Auth에서 관리 |
| 사용자 ID | `users.id` Integer | `uuid`, `auth.users.id` 연결 |
| 사용자 FK | Integer | `uuid` |
| 일반 ID | Integer | Integer 유지 |
| 그룹 인원 | `groups.members` 저장 | 컬럼 제거, `group_members` 집계 |
| 그룹 권한 | 별도 정의 없음 | 그룹장·역할·상태 없음, 모두 동일 권한 |
| 초대 | 초대 코드 | 초대 코드 유지 |
| 개인 호칭 | 다른 테이블 기본값 참조 | 가입 시 애플리케이션이 복사 후 개별 수정 |
| 기억 기록 인덱스 | `(group_id, record_date)` | `(patient_id, record_date)` |
| 시간 타입 | `Timestamp` | `timestamptz` |
| 업데이트 시간 | `on update` 표기 | PostgreSQL 트리거 적용 |
| 첨부파일 값 | `file_url` | 컬럼명 유지, 실제 값은 Storage 경로 |
| RLS | 별도 명시 없음 | 그룹 멤버 및 작성자 기준 적용 |

# Application structure

The `app` package follows a layered FastAPI structure while keeping the product domains visible.

```text
request
  -> api/v1/endpoints  HTTP routing and dependency wiring
  -> services          use cases, authorization, and business rules
  -> repositories      Supabase queries and persistence
  -> db                 database client infrastructure
```

- `core`: settings, authentication/security helpers, and application exceptions
- `schemas`: Pydantic request/response contracts; these are API types, not database tables
- `integrations`: emotion-analysis and Supabase Storage adapters
- `api/dependencies.py`: current-user and group-membership dependencies shared by endpoints

Domain file mapping:

| Domain | Main DB tables |
| --- | --- |
| users | `users` |
| groups | `groups`, `group_members`, `member_cheers` |
| patients | `patients` |
| diaries | `diaries`, `emotions`, `emotion_tags`, `diary_selected_emotion_tags`, `flowers` |
| memories | `memory_records`, bookmarks, comments, reactions |
| care_notes | daily conditions, behavior logs, medications, intake logs, hospital visits |
| media | `media` and Storage access |

Keep authorization in both the API/service layer and Supabase RLS. The server's service-role key bypasses RLS, so every group-scoped use case must validate the authenticated user's membership.

## Group API and database contract

The group implementation is in `api/v1/endpoints/groups.py`, `services/groups.py`,
`repositories/groups.py`, and `schemas/groups.py`. Read this section before changing
or reviewing a group feature; it records the API/DB contract extracted from
`API_00.pdf` and `DB_3.pdf` on 2026-09-14.

All endpoints require `Authorization: Bearer <access_token>`.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/groups` | Create a group and add its creator as a member |
| GET | `/api/v1/groups` | List the current user's groups |
| POST | `/api/v1/groups/join` | Join by `invite_code` |
| GET/PATCH | `/api/v1/groups/{group_id}` | Read or update a group; membership required |
| GET | `/api/v1/groups/{group_id}/members` | List members; membership required |
| PATCH/DELETE | `/api/v1/groups/{group_id}/members/me` | Update the caller's nickname/relation or leave |
| POST | `/api/v1/groups/{group_id}/members/{member_user_id}/cheers` | Send one daily cheer to another member |

`groups` stores `invite_code`, `group_name`, optional profile image, and timestamps.
`group_members` is unique on `(user_id, group_id)` and stores each member's patient
nickname and relation. `member_cheers` is unique on
`(sender_user_id, receiver_user_id, cheer_date)`, so repeated cheers on the same day
are rejected. The service repeats all membership checks because the configured
Supabase service-role client bypasses RLS.

The API specification only supplies `invite_code` for creation/join membership data,
while the current database makes `patients_nickname` and `patient_relation` required.
The implementation therefore creates those records with the explicit temporary
defaults `"환자"` and `"보호자"`; clients should update them through the `members/me`
endpoint. Change this only after the API request contract is expanded.

### Current schema gaps

The supplied API/DB documents describe `anonymous_letters` endpoints and a
`joined_at` membership timestamp. The currently tracked Supabase migration has
neither `anonymous_letters` nor `group_members.joined_at`, so letter endpoints were
intentionally not implemented and `joined_at` is returned as `null`. Add and apply a
database migration first, then implement the documented letter endpoints. The
documents also mention a `groups.members` column; this backend calculates
`member_count` from `group_members` so it remains correct with the current schema.

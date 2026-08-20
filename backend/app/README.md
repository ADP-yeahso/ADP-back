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

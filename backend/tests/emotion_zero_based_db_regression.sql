-- LOCAL disposable PostgreSQL only. Apply the bootstrap and all migrations
-- before 20261028, then run this file with psql -v ON_ERROR_STOP=1 -f ... .
-- This exercises existing data migration, SQL Editor retries and new RPC writes.
insert into auth.users values ('00000000-0000-0000-0000-000000000901');
insert into public.users(id, email, name, phone_number) values
  ('00000000-0000-0000-0000-000000000901', 'labels@example.test', 'labels', 'labels');
insert into public.groups(id, invite_code, group_name) values (901, 'labels', 'labels');

insert into public.flowers(id, emotion_id, flower_name, sentence)
select 900 + id, id, emotion, 'preserved flower' from public.emotions;

insert into public.diaries(id, user_id, group_id, situation_text,
  question_answer_text, final_emotion_id, correct_emotion_id, flower_id,
  ai_emotion_predictions, status, emotion_logic_version, finalized_at)
select 900 + e.id, '00000000-0000-0000-0000-000000000901', 901, 'situation',
  'answer', e.id, e.id, 900 + e.id,
  (select jsonb_agg(jsonb_build_object('rank', ranked.rank,
    'emotion_id', predicted.id, 'emotion', predicted.emotion,
    'display_name', predicted.display_name, 'confidence', 0.5,
    'tags', (select jsonb_agg(to_jsonb(t) order by t.display_order)
      from public.emotion_tags t where t.parent_emotion_id = predicted.id))
    order by ranked.rank)
    from (values (1, e.id), (2, e.id % 7 + 1)) ranked(rank, emotion_id)
    join public.emotions predicted on predicted.id = ranked.emotion_id),
  'completed', 2, '2026-10-01T00:00:00Z'::timestamptz
from public.emotions e;

insert into public.diary_selected_emotion_tags(diary_id, emotion_tag_id)
select d.id, t.id from public.diaries d
join public.emotion_tags t on t.parent_emotion_id = d.final_emotion_id
where t.display_order <= 3;

insert into public.emotion_training_samples(diary_id, user_id, situation_text,
  question_answer_text, final_emotion_id, correct_emotion_id, ai_predicted_emotion_id)
select id, user_id, situation_text, question_answer_text,
  final_emotion_id, correct_emotion_id, final_emotion_id from public.diaries;

-- Legacy and untouched drafts include NULL IDs and empty prediction arrays.
insert into public.diaries(id, user_id, group_id, final_emotion_id)
values (910, '00000000-0000-0000-0000-000000000901', 901, 7),
  (911, '00000000-0000-0000-0000-000000000901', 901, null);

create temporary table original_tags as select * from public.emotion_tags;
create temporary table original_selections as select * from public.diary_selected_emotion_tags;
create temporary table original_constraints as
select conrelid, conname, pg_get_constraintdef(oid) as definition
from pg_constraint where contype = 'f' and confrelid = 'public.emotions'::regclass;

-- Production also enforces unique tag ordering within each parent emotion.
alter table public.emotion_tags
  add constraint emotion_tags_parent_display_order_unique
  unique (parent_emotion_id, display_order);

\ir ../../supabase/migrations/20261028_zero_based_emotion_ids.sql

do $$
begin
  assert (select array_agg(emotion order by id) = array[
    'neutral', 'anger', 'anxiety', 'sadness', 'guilt', 'gratitude', 'tenderness']::varchar[]
    and array_agg(id order by id) = array[0,1,2,3,4,5,6] from public.emotions);
  assert not exists (select 1 from public.emotion_tags t
    join original_tags original using (id)
    where t.parent_emotion_id <> original.parent_emotion_id % 7
      or (to_jsonb(t) - 'parent_emotion_id') <> (to_jsonb(original) - 'parent_emotion_id'));
  assert not exists (select * from original_selections except select * from public.diary_selected_emotion_tags);
  assert (select count(*) = 7 from public.flowers where emotion_id = (id - 900) % 7);
  assert (select count(*) = 7 from public.diaries
    where id between 901 and 907 and final_emotion_id = (id - 900) % 7
      and correct_emotion_id = (id - 900) % 7 and flower_id = id
      and status = 'completed' and emotion_logic_version = 2
      and finalized_at = '2026-10-01T00:00:00Z'::timestamptz);
  assert (select count(*) = 7 from public.emotion_training_samples
    where final_emotion_id = (diary_id - 900) % 7 and correct_emotion_id = (diary_id - 900) % 7
      and ai_predicted_emotion_id = (diary_id - 900) % 7);
  assert (select final_emotion_id = 0 and correct_emotion_id is null
    and ai_emotion_predictions = '[]'::jsonb from public.diaries where id = 910);
  assert (select final_emotion_id is null and correct_emotion_id is null
    and ai_emotion_predictions = '[]'::jsonb from public.diaries where id = 911);
  assert not exists (
    select 1 from public.diaries d
    cross join jsonb_array_elements(d.ai_emotion_predictions) with ordinality p(value, rank)
    left join public.emotions e on e.id = (p.value->>'emotion_id')::integer
    where e.emotion is distinct from p.value->>'emotion'
      or (p.value->>'rank')::integer <> p.rank or (p.value->>'confidence')::numeric <> 0.5
      or p.value->'tags' <> (select jsonb_agg(to_jsonb(t) order by t.display_order)
        from public.emotion_tags t where t.parent_emotion_id = e.id)
  );
  assert not exists (select * from original_constraints except
    select conrelid, conname, pg_get_constraintdef(oid)
    from pg_constraint where contype = 'f' and confrelid = 'public.emotions'::regclass);
  assert exists (select 1 from pg_constraint
    where conrelid = 'public.emotion_tags'::regclass
      and conname = 'emotion_tags_parent_display_order_unique' and contype = 'u' and convalidated);
end;
$$;

create temporary table converted_diaries as select * from public.diaries;
\ir ../../supabase/migrations/20261028_zero_based_emotion_ids.sql
do $$
begin
  assert not exists (select * from converted_diaries except select * from public.diaries);
end;
$$;

-- RPC regression uses neutral (ID 0) as AI primary and as the user-majority label.
\ir emotion_db_regression.sql

-- The RPC test's rollback must leave the already-applied migration in place.
do $$
begin
  assert (select array_agg(id order by id) = array[0,1,2,3,4,5,6] from public.emotions);
end;
$$;

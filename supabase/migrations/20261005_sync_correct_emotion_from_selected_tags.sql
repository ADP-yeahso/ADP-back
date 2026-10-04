-- Ensure the user-majority emotion is persisted as soon as the three selected
-- tags are stored. This also protects deployments where the transition RPC was
-- applied before the ground-truth assignment was added.
begin;

create or replace function public.sync_diary_correct_emotion_from_tags()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  target_diary_id integer := coalesce(new.diary_id, old.diary_id);
  majority_emotion_id integer;
  majority_votes integer;
begin
  select (prediction.value->>'emotion_id')::integer, count(*)::integer
    into majority_emotion_id, majority_votes
  from public.diaries d
  cross join jsonb_array_elements(d.ai_emotion_predictions) prediction
  cross join jsonb_array_elements(prediction.value->'tags') suggested_tag
  join public.diary_selected_emotion_tags selected_tag
    on selected_tag.diary_id = d.id
   and selected_tag.emotion_tag_id = (suggested_tag.value->>'id')::integer
  where d.id = target_diary_id
  group by (prediction.value->>'emotion_id')::integer
  order by count(*) desc
  limit 1;

  update public.diaries
     set correct_emotion_id = case
       when majority_votes >= 2 then majority_emotion_id
       else null
     end
   where id = target_diary_id;

  if tg_op = 'DELETE' then
    return old;
  end if;
  return new;
end;
$$;

drop trigger if exists diary_selected_tags_sync_correct_emotion
  on public.diary_selected_emotion_tags;

create trigger diary_selected_tags_sync_correct_emotion
after insert or update or delete on public.diary_selected_emotion_tags
for each row execute function public.sync_diary_correct_emotion_from_tags();

-- Backfill diaries whose three selected tags were saved before this trigger
-- was installed.
with majority as (
  select distinct on (d.id)
    d.id as diary_id,
    (prediction.value->>'emotion_id')::integer as emotion_id,
    count(*)::integer as votes
  from public.diaries d
  cross join jsonb_array_elements(d.ai_emotion_predictions) prediction
  cross join jsonb_array_elements(prediction.value->'tags') suggested_tag
  join public.diary_selected_emotion_tags selected_tag
    on selected_tag.diary_id = d.id
   and selected_tag.emotion_tag_id = (suggested_tag.value->>'id')::integer
  group by d.id, (prediction.value->>'emotion_id')::integer
  order by d.id, count(*) desc
)
update public.diaries d
   set correct_emotion_id = majority.emotion_id
  from majority
 where d.id = majority.diary_id
   and majority.votes >= 2;

comment on function public.sync_diary_correct_emotion_from_tags() is
  'Stores the majority parent emotion of the three selected tags in diaries.correct_emotion_id.';

notify pgrst, 'reload schema';
commit;

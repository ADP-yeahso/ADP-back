-- Apply BEFORE deploying the corresponding backend. Existing completed records
-- keep their historical final_emotion_id (version 1); do not invent AI rankings.
begin;

alter table public.diaries
  add column if not exists correct_emotion_id integer references public.emotions(id),
  add column if not exists ai_emotion_predictions jsonb not null default '[]'::jsonb,
  add column if not exists emotion_logic_version integer not null default 1,
  add column if not exists finalized_at timestamptz;

comment on column public.diaries.final_emotion_id is
  'Version 2: saved AI rank-1 emotion. Version 1: legacy user-majority emotion.';
comment on column public.diaries.correct_emotion_id is
  'Ground-truth emotion: majority parent of three user-selected tags.';
comment on column public.diaries.ai_emotion_predictions is
  'Ordered immutable snapshot of two predictions with rank, confidence and five tags each.';

update public.diaries set correct_emotion_id = final_emotion_id
where status = 'completed' and emotion_logic_version = 1 and correct_emotion_id is null;

alter table public.emotion_training_samples
  add column if not exists ai_predicted_emotion_id integer references public.emotions(id),
  add column if not exists correct_emotion_id integer references public.emotions(id);
update public.emotion_training_samples set correct_emotion_id = final_emotion_id
where correct_emotion_id is null;
comment on column public.emotion_training_samples.final_emotion_id is
  'Legacy training-target column; remains the USER ground truth for compatibility.';

-- The API supplies the verified user UUID. Only service_role may call this RPC.
-- Row locking keeps answer edits, snapshots, selections and finalization consistent.
create or replace function public.apply_diary_emotion_transition(
  p_diary_id integer, p_user_id uuid, p_action text, p_payload jsonb
) returns public.diaries
language plpgsql security definer set search_path = public
as $$
declare
  d public.diaries;
  predictions jsonb;
  prediction jsonb;
  tag jsonb;
  ids integer[];
  allowed_ids integer[];
  primary_id integer;
  correct_id integer;
  flower integer;
  votes integer;
  reset_analysis boolean := false;
begin
  select * into d from public.diaries
  where id = p_diary_id and user_id = p_user_id and deleted_at is null for update;
  if not found then
    raise sqlstate 'PT404' using message = 'Diary not found';
  end if;
  if d.status = 'completed' then
    if p_action = 'finalize' then return d; end if;
    raise sqlstate 'PT409' using message = 'Finalized diary cannot be edited';
  end if;

  if p_action = 'answer' then
    if d.ai_question_text is null then
      raise sqlstate 'PT409' using message = 'AI question has not been generated';
    end if;
    if coalesce(length(trim(p_payload->>'answer')), 0) = 0 then
      raise sqlstate 'PT422' using message = 'Answer is required';
    end if;
    reset_analysis := d.question_answer_text is distinct from p_payload->>'answer';
    d.question_answer_text := p_payload->>'answer';
  elsif p_action = 'question' then
    if d.situation_text is distinct from p_payload->>'situation_text' then
      raise sqlstate 'PT409' using message = 'Situation changed; generate the question again';
    end if;
    d.ai_question_text := p_payload->>'question';
    d.question_answer_text := null;
    reset_analysis := true;
  elsif p_action = 'update' then
    if p_payload ? 'title' then d.title := p_payload->>'title'; end if;
    if p_payload->>'record_date' is not null then
      d.record_date := (p_payload->>'record_date')::timestamptz;
    end if;
    if p_payload->>'situation_text' is not null
      and d.situation_text is distinct from p_payload->>'situation_text' then
      d.situation_text := p_payload->>'situation_text';
      d.ai_question_text := null;
      d.question_answer_text := null;
      reset_analysis := true;
    end if;
  elsif p_action = 'predictions' then
    if d.question_answer_text is null
      or d.question_answer_text is distinct from p_payload->>'answer' then
      raise sqlstate 'PT409' using message = 'Answer changed; request suggestions again';
    end if;
    if jsonb_array_length(d.ai_emotion_predictions) > 0 then return d; end if;
    predictions := p_payload->'predictions';
    if jsonb_typeof(predictions) is distinct from 'array' then
      raise sqlstate 'PT422' using message = 'Two predictions are required';
    end if;
    if jsonb_array_length(predictions) <> 2
      or (predictions->0->>'rank')::integer is distinct from 1
      or (predictions->1->>'rank')::integer is distinct from 2
      or predictions->0->>'emotion_id' = predictions->1->>'emotion_id' then
      raise sqlstate 'PT422' using message = 'Two distinct ranked emotions are required';
    end if;
    for prediction in select value from jsonb_array_elements(predictions) loop
      if not exists (select 1 from public.emotions
        where id = (prediction->>'emotion_id')::integer and emotion = prediction->>'emotion') then
        raise sqlstate 'PT422' using message = 'Unknown emotion';
      end if;
      if jsonb_typeof(prediction->'tags') is distinct from 'array' then
        raise sqlstate 'PT422' using message = 'Five tags per emotion are required';
      end if;
      if jsonb_array_length(prediction->'tags') <> 5 or
        (select count(distinct value->>'id') from jsonb_array_elements(prediction->'tags')) <> 5 then
        raise sqlstate 'PT422' using message = 'Five distinct tags per emotion are required';
      end if;
      for tag in select value from jsonb_array_elements(prediction->'tags') loop
        if not exists (select 1 from public.emotion_tags
          where id = (tag->>'id')::integer
          and parent_emotion_id = (prediction->>'emotion_id')::integer
          and parent_emotion_id = (tag->>'parent_emotion_id')::integer and is_active) then
          raise sqlstate 'PT422' using message = 'Invalid suggested tag';
        end if;
      end loop;
    end loop;
    d.ai_emotion_predictions := predictions;
    d.final_emotion_id := (predictions->0->>'emotion_id')::integer;
    d.correct_emotion_id := null;
    d.flower_id := null;
    d.emotion_logic_version := 2;
    delete from public.diary_selected_emotion_tags where diary_id = d.id;
  elsif p_action in ('tags', 'finalize') then
    if jsonb_array_length(d.ai_emotion_predictions) <> 2 or d.question_answer_text is null then
      raise sqlstate 'PT409' using message = 'Request emotion suggestions first';
    end if;
    select array_agg((t.value->>'id')::integer) into allowed_ids
    from jsonb_array_elements(d.ai_emotion_predictions) p,
         jsonb_array_elements(p.value->'tags') t;
    if p_action = 'tags' then
      select array_agg(value::integer) into ids
      from jsonb_array_elements_text(p_payload->'tag_ids');
    else
      select array_agg(emotion_tag_id) into ids
      from public.diary_selected_emotion_tags where diary_id = d.id;
    end if;
    if coalesce(cardinality(ids), 0) <> 3
      or (select count(distinct i) from unnest(ids) i) <> 3
      or not ids <@ allowed_ids then
      raise sqlstate 'PT422' using message = 'Select three distinct tags from the saved predictions';
    end if;
    -- Count snapshot parents, not mutable lookup-table metadata.
    select (p.value->>'emotion_id')::integer, count(*) into correct_id, votes
    from jsonb_array_elements(d.ai_emotion_predictions) p,
         jsonb_array_elements(p.value->'tags') t
    where (t.value->>'id')::integer = any(ids)
    group by (p.value->>'emotion_id')::integer order by count(*) desc limit 1;
    if votes < 2 then
      raise sqlstate 'PT422' using message = 'A majority emotion is required';
    end if;
    d.correct_emotion_id := correct_id;
    if p_action = 'tags' then
      delete from public.diary_selected_emotion_tags where diary_id = d.id;
      insert into public.diary_selected_emotion_tags(diary_id, emotion_tag_id)
      select d.id, i from unnest(ids) i;
    else
      primary_id := (d.ai_emotion_predictions->0->>'emotion_id')::integer;
      flower := (p_payload->>'flower_id')::integer;
      if not exists (select 1 from public.flowers where id = flower and emotion_id = primary_id) then
        raise sqlstate 'PT409' using message = 'Flower must match the saved AI primary emotion';
      end if;
      d.final_emotion_id := primary_id;
      d.flower_id := flower;
      d.status := 'completed';
      d.finalized_at := now();
      insert into public.emotion_training_samples
        (diary_id, user_id, situation_text, question_answer_text, final_emotion_id,
         ai_predicted_emotion_id, correct_emotion_id)
      values (d.id, d.user_id, d.situation_text, d.question_answer_text,
              correct_id, primary_id, correct_id);
    end if;
  else
    raise sqlstate 'PT422' using message = 'Unknown diary transition';
  end if;

  if reset_analysis then
    d.ai_emotion_predictions := '[]'::jsonb;
    d.final_emotion_id := null;
    d.correct_emotion_id := null;
    d.flower_id := null;
    d.finalized_at := null;
    delete from public.diary_selected_emotion_tags where diary_id = d.id;
  end if;
  update public.diaries set title = d.title, situation_text = d.situation_text,
    ai_question_text = d.ai_question_text, question_answer_text = d.question_answer_text,
    ai_emotion_predictions = d.ai_emotion_predictions, final_emotion_id = d.final_emotion_id,
    correct_emotion_id = d.correct_emotion_id, flower_id = d.flower_id, status = d.status,
    emotion_logic_version = d.emotion_logic_version, finalized_at = d.finalized_at,
    record_date = d.record_date where id = d.id returning * into d;
  return d;
end;
$$;

revoke all on function public.apply_diary_emotion_transition(integer, uuid, text, jsonb)
  from public, anon, authenticated;
grant execute on function public.apply_diary_emotion_transition(integer, uuid, text, jsonb)
  to service_role;
notify pgrst, 'reload schema';
commit;

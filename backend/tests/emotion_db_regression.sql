-- Run after all migrations on a disposable database (including emotion ID 0).
begin;
insert into auth.users values ('00000000-0000-0000-0000-000000000001');
insert into public.users(id,email,name,phone_number) values
 ('00000000-0000-0000-0000-000000000001','test@example.test','test','test');
insert into public.groups(id,invite_code,group_name) values(1,'test','test');
insert into public.diaries(id,user_id,group_id,situation_text,ai_question_text,question_answer_text)
values (1,'00000000-0000-0000-0000-000000000001',1,'situation','question','answer');
insert into public.flowers(id,emotion_id,flower_name,sentence)
select 1,id,'flower','sentence' from public.emotions where emotion='neutral';

do $$
declare
  uid uuid := '00000000-0000-0000-0000-000000000001';
  predictions jsonb;
  d public.diaries;
  first_id integer;
  second_id integer;
  a integer[];
  b integer[];
  choice integer[];
begin
  select id into first_id from public.emotions where emotion='neutral';
  select id into second_id from public.emotions where emotion='sadness';
  select array_agg(id order by id) into a from public.emotion_tags where parent_emotion_id=first_id;
  select array_agg(id order by id) into b from public.emotion_tags where parent_emotion_id=second_id;
  select jsonb_agg(jsonb_build_object('rank',rank,'emotion_id',e.id,'emotion',e.emotion,
    'display_name',e.display_name,'confidence',0.5,'tags',
    (select jsonb_agg(to_jsonb(t) order by t.display_order) from public.emotion_tags t
      where t.parent_emotion_id=e.id)) order by rank) into predictions
  from (values(1,first_id),(2,second_id)) ranked(rank,id) join public.emotions e using(id);
  d := public.apply_diary_emotion_transition(1,uid,'predictions',
    jsonb_build_object('answer','answer','predictions',predictions));
  assert d.final_emotion_id=first_id and d.correct_emotion_id is null;
  assert jsonb_array_length(d.ai_emotion_predictions)=2;

  -- Duplicate IDs and out-of-snapshot IDs must not overwrite the selection.
  begin
    perform public.apply_diary_emotion_transition(1,uid,'tags',jsonb_build_object('tag_ids',array[a[1],a[1],b[1]]));
    raise exception 'Duplicate tags accepted';
  exception when sqlstate 'PT422' then null; end;
  begin
    perform public.apply_diary_emotion_transition(1,uid,'tags',jsonb_build_object('tag_ids',array[a[1],b[1],9999]));
    raise exception 'Unknown tags accepted';
  exception when sqlstate 'PT422' then null; end;

  -- 2:1 and 3:0 votes work for either ranked emotion.
  foreach choice slice 1 in array array[array[a[1],a[2],b[1]],array[a[1],a[2],a[3]]] loop
    d := public.apply_diary_emotion_transition(1,uid,'tags',jsonb_build_object('tag_ids',choice));
    assert d.correct_emotion_id=first_id and d.final_emotion_id=first_id;
  end loop;
  foreach choice slice 1 in array array[array[a[1],b[1],b[2]],array[b[1],b[2],b[3]]] loop
    d := public.apply_diary_emotion_transition(1,uid,'tags',jsonb_build_object('tag_ids',choice));
    assert d.correct_emotion_id=second_id and d.final_emotion_id=first_id;
  end loop;
  -- Same-answer retries preserve the snapshot and selection.
  d := public.apply_diary_emotion_transition(1,uid,'answer','{"answer":"answer"}');
  assert d.correct_emotion_id=second_id;
  d := public.apply_diary_emotion_transition(1,uid,'answer','{"answer":"new answer"}');
  assert d.final_emotion_id is null and d.correct_emotion_id is null;
  assert d.ai_emotion_predictions='[]'::jsonb;
  assert (select count(*)=0 from public.diary_selected_emotion_tags where diary_id=1);
  begin
    perform public.apply_diary_emotion_transition(1,uid,'predictions',jsonb_build_object('answer','answer','predictions',predictions));
    raise exception 'Stale inference accepted';
  exception when sqlstate 'PT409' then null; end;
  d := public.apply_diary_emotion_transition(1,uid,'predictions',jsonb_build_object('answer','new answer','predictions',predictions));
  d := public.apply_diary_emotion_transition(1,uid,'tags',jsonb_build_object('tag_ids',array[a[1],b[1],b[2]]));
  begin
    perform public.apply_diary_emotion_transition(1,uid,'finalize','{"flower_id":9999}');
    raise exception 'Unknown flower accepted';
  exception when sqlstate 'PT409' then null; end;
  assert (select count(*)=0 from public.emotion_training_samples where diary_id=1);
  d := public.apply_diary_emotion_transition(1,uid,'finalize','{"flower_id":1}');
  assert d.final_emotion_id=first_id and d.correct_emotion_id=second_id;
  assert d.status='completed' and d.finalized_at is not null and d.emotion_logic_version=2;
  assert (select final_emotion_id=second_id and correct_emotion_id=second_id
    and ai_predicted_emotion_id=first_id and question_answer_text='new answer'
    from public.emotion_training_samples where diary_id=1);
  d := public.apply_diary_emotion_transition(1,uid,'finalize','{"flower_id":1}');
  assert (select count(*)=1 from public.emotion_training_samples where diary_id=1);
  begin
    perform public.apply_diary_emotion_transition(1,uid,'answer','{"answer":"edit"}');
    raise exception 'Completed diary edited';
  exception when sqlstate 'PT409' then null; end;
  begin
    perform public.apply_diary_emotion_transition(1,'00000000-0000-0000-0000-000000000002','finalize','{"flower_id":1}');
    raise exception 'Cross-user access accepted';
  exception when sqlstate 'PT404' then null; end;
  assert not has_function_privilege('authenticated','public.apply_diary_emotion_transition(integer,uuid,text,jsonb)','EXECUTE');
  assert has_function_privilege('service_role','public.apply_diary_emotion_transition(integer,uuid,text,jsonb)','EXECUTE');
end;
$$;
rollback;

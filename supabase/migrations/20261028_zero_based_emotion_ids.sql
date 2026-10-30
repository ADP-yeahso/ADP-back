-- Change only neutral from 7 to 0; keep the original emotion IDs 1..6.
-- Also repairs the previously supplied SQL that incorrectly shifted every ID.
-- Run this entire DO block. It is atomic and needs no temporary tables/session.
do $emotion_ids$
declare
  id_mapping jsonb;
  foreign_keys jsonb;
  foreign_key jsonb;
  emotion_row record;
begin
  lock table public.emotions in access exclusive mode;

  select coalesce(jsonb_agg(jsonb_build_object(
    'old_id', e.id, 'new_id', labels.id)), '[]'::jsonb)
    into id_mapping
  from public.emotions e
  join (values
    (1, 'anger'), (2, 'anxiety'), (3, 'sadness'), (4, 'guilt'),
    (5, 'gratitude'), (6, 'tenderness'), (0, 'neutral')
  ) as labels(id, emotion) using (emotion);

  if (select count(*) from public.emotions) <> 7
    or jsonb_array_length(id_mapping) <> 7 then
    raise exception 'Expected exactly the seven known emotions';
  end if;

  -- SQL Editor retries must not shift existing zero-based data a second time.
  if not exists (select 1 from jsonb_to_recordset(id_mapping)
    as m(old_id integer, new_id integer) where old_id <> new_id) then
    return;
  end if;
  if not (
    (select bool_and(old_id = case when new_id = 0 then 7 else new_id end)
      from jsonb_to_recordset(id_mapping) as m(old_id integer, new_id integer))
    or
    (select bool_and(old_id = case when new_id = 0 then 6 else new_id - 1 end)
      from jsonb_to_recordset(id_mapping) as m(old_id integer, new_id integer))
  ) then
    raise exception 'Unexpected emotion IDs; expected original, previously shifted, or corrected labels';
  end if;

  -- Discover every foreign key, including any additional referencing tables.
  -- Preserve original definitions, delete actions and deferrability in memory.
  select coalesce(jsonb_agg(jsonb_build_object(
    'table_name', format('%I.%I', n.nspname, t.relname),
    'constraint_name', c.conname,
    'definition', pg_get_constraintdef(c.oid),
    'column_name', a.attname,
    'column_count', cardinality(c.conkey),
    'references_id', c.confkey = array[(select attnum from pg_attribute
      where attrelid = 'public.emotions'::regclass and attname = 'id')]
  )), '[]'::jsonb) into foreign_keys
  from pg_constraint c
  join pg_class t on t.oid = c.conrelid
  join pg_namespace n on n.oid = t.relnamespace
  join pg_attribute a on a.attrelid = c.conrelid and a.attnum = c.conkey[1]
  where c.contype = 'f' and c.confrelid = 'public.emotions'::regclass;

  for foreign_key in select value from jsonb_array_elements(foreign_keys) loop
    if (foreign_key->>'column_count')::integer <> 1
      or not (foreign_key->>'references_id')::boolean then
      raise exception 'Unsupported emotion foreign key; no data was changed';
    end if;
    execute format('lock table %s in access exclusive mode', foreign_key->>'table_name');
  end loop;

  -- Validate snapshot IDs before rebuilding arrays; never silently lose entries.
  if exists (
    select 1 from public.diaries d
    cross join jsonb_array_elements(d.ai_emotion_predictions) p
    left join jsonb_to_recordset(id_mapping) as m(old_id integer, new_id integer)
      on m.old_id = (p.value->>'emotion_id')::integer
    where m.old_id is null or exists (
      select 1 from jsonb_array_elements(p.value->'tags') t
      left join jsonb_to_recordset(id_mapping) as tm(old_id integer, new_id integer)
        on tm.old_id = (t.value->>'parent_emotion_id')::integer
      where tm.old_id is null
    )
  ) then
    raise exception 'Unknown emotion ID in saved AI predictions; no data was changed';
  end if;

  for foreign_key in select value from jsonb_array_elements(foreign_keys) loop
    execute format('alter table %s drop constraint %I',
      foreign_key->>'table_name', foreign_key->>'constraint_name');
  end loop;

  -- Use unused IDs temporarily to avoid collisions when repairing shifted data.
  -- All changes, including these intermediate IDs, belong to this one DO block.
  for emotion_row in select * from jsonb_to_recordset(id_mapping)
    as m(old_id integer, new_id integer) where old_id <> new_id loop
    update public.emotions set id = emotion_row.old_id + 8 where id = emotion_row.old_id;
  end loop;
  for emotion_row in select * from jsonb_to_recordset(id_mapping)
    as m(old_id integer, new_id integer) where old_id <> new_id loop
    update public.emotions set id = emotion_row.new_id where id = emotion_row.old_id + 8;
  end loop;

  -- Referencing columns need the same two-phase move: updating directly would
  -- temporarily duplicate UNIQUE(parent_emotion_id, display_order) tag keys.
  -- Keep every unique constraint active throughout the conversion.
  for foreign_key in select value from jsonb_array_elements(foreign_keys) loop
    execute format('update %s as target set %I = mapping.old_id + 8
      from jsonb_to_recordset($1) as mapping(old_id integer, new_id integer)
      where target.%I = mapping.old_id and mapping.old_id <> mapping.new_id',
      foreign_key->>'table_name', foreign_key->>'column_name', foreign_key->>'column_name')
      using id_mapping;
  end loop;

  for foreign_key in select value from jsonb_array_elements(foreign_keys) loop
    execute format('update %s as target set %I = mapping.new_id
      from jsonb_to_recordset($1) as mapping(old_id integer, new_id integer)
      where target.%I = mapping.old_id + 8 and mapping.old_id <> mapping.new_id',
      foreign_key->>'table_name', foreign_key->>'column_name', foreign_key->>'column_name')
      using id_mapping;
  end loop;

  -- Preserve prediction/tag order, tag IDs, ranks, probabilities and all metadata.
  update public.diaries d set ai_emotion_predictions = (
    select jsonb_agg(jsonb_set(
      jsonb_set(p.value, '{emotion_id}', to_jsonb(m.new_id)),
      '{tags}', (select coalesce(jsonb_agg(
        jsonb_set(t.value, '{parent_emotion_id}', to_jsonb(tm.new_id))
        order by t.position), '[]'::jsonb)
        from jsonb_array_elements(p.value->'tags') with ordinality t(value, position)
        join jsonb_to_recordset(id_mapping) as tm(old_id integer, new_id integer)
          on tm.old_id = (t.value->>'parent_emotion_id')::integer)
      ) order by p.position)
    from jsonb_array_elements(d.ai_emotion_predictions) with ordinality p(value, position)
    join jsonb_to_recordset(id_mapping) as m(old_id integer, new_id integer)
      on m.old_id = (p.value->>'emotion_id')::integer
  ) where jsonb_array_length(d.ai_emotion_predictions) > 0;

  for foreign_key in select value from jsonb_array_elements(foreign_keys) loop
    execute format('alter table %s add constraint %I %s',
      foreign_key->>'table_name', foreign_key->>'constraint_name', foreign_key->>'definition');
  end loop;

  comment on column public.emotions.id is
    'Fixed labels: 0=neutral, 1=anger, 2=anxiety, 3=sadness, 4=guilt, 5=gratitude, 6=tenderness. Original IDs 1..6 are unchanged; only neutral moves from 7 to 0.';
  perform pg_notify('pgrst', 'reload schema');
end;
$emotion_ids$;

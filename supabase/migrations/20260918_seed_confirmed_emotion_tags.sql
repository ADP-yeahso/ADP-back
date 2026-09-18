-- Synchronise the seven confirmed emotion categories with exactly five active
-- selectable tags each. Existing tag IDs are retained by display order.
with seed(emotion, tag_name, display_order) as (
  values
    ('anger', '억울함', 1), ('anger', '짜증', 2), ('anger', '무력감', 3), ('anger', '원망스러운', 4), ('anger', '분함', 5),
    ('anxiety', '막막함', 1), ('anxiety', '예민함', 2), ('anxiety', '압박감', 3), ('anxiety', '당혹감', 4), ('anxiety', '초조함', 5),
    ('sadness', '상실감', 1), ('sadness', '탈진', 2), ('sadness', '서러움', 3), ('sadness', '허무함', 4), ('sadness', '외로움', 5),
    ('guilt', '자책감', 1), ('guilt', '미안함', 2), ('guilt', '부족함', 3), ('guilt', '후회스러움', 4), ('guilt', '부끄러움', 5),
    ('gratitude', '다행스러움', 1), ('gratitude', '따뜻함', 2), ('gratitude', '편안함', 3), ('gratitude', '고마움', 4), ('gratitude', '후련함', 5),
    ('tenderness', '그리움', 1), ('tenderness', '뭉클함', 2), ('tenderness', '사랑스러움', 3), ('tenderness', '소중함', 4), ('tenderness', '애틋함', 5),
    ('neutral', '담담함', 1), ('neutral', '무탈함', 2), ('neutral', '여유로움', 3), ('neutral', '무심함', 4), ('neutral', '평온함', 5)
)
update public.emotion_tags tag
set tag_name = seed.tag_name, is_active = true
from public.emotions emotion
join seed on seed.emotion = emotion.emotion
where tag.parent_emotion_id = emotion.id and tag.display_order = seed.display_order;

with seed(emotion, tag_name, display_order) as (
  values
    ('anger', '억울함', 1), ('anger', '짜증', 2), ('anger', '무력감', 3), ('anger', '원망스러운', 4), ('anger', '분함', 5),
    ('anxiety', '막막함', 1), ('anxiety', '예민함', 2), ('anxiety', '압박감', 3), ('anxiety', '당혹감', 4), ('anxiety', '초조함', 5),
    ('sadness', '상실감', 1), ('sadness', '탈진', 2), ('sadness', '서러움', 3), ('sadness', '허무함', 4), ('sadness', '외로움', 5),
    ('guilt', '자책감', 1), ('guilt', '미안함', 2), ('guilt', '부족함', 3), ('guilt', '후회스러움', 4), ('guilt', '부끄러움', 5),
    ('gratitude', '다행스러움', 1), ('gratitude', '따뜻함', 2), ('gratitude', '편안함', 3), ('gratitude', '고마움', 4), ('gratitude', '후련함', 5),
    ('tenderness', '그리움', 1), ('tenderness', '뭉클함', 2), ('tenderness', '사랑스러움', 3), ('tenderness', '소중함', 4), ('tenderness', '애틋함', 5),
    ('neutral', '담담함', 1), ('neutral', '무탈함', 2), ('neutral', '여유로움', 3), ('neutral', '무심함', 4), ('neutral', '평온함', 5)
)
insert into public.emotion_tags (parent_emotion_id, tag_name, display_order, is_active)
select emotion.id, seed.tag_name, seed.display_order, true
from seed
join public.emotions emotion on emotion.emotion = seed.emotion
where not exists (
  select 1 from public.emotion_tags tag
  where tag.parent_emotion_id = emotion.id and tag.display_order = seed.display_order
);

with seed(emotion, display_order) as (
  values
    ('anger', 1), ('anger', 2), ('anger', 3), ('anger', 4), ('anger', 5),
    ('anxiety', 1), ('anxiety', 2), ('anxiety', 3), ('anxiety', 4), ('anxiety', 5),
    ('sadness', 1), ('sadness', 2), ('sadness', 3), ('sadness', 4), ('sadness', 5),
    ('guilt', 1), ('guilt', 2), ('guilt', 3), ('guilt', 4), ('guilt', 5),
    ('gratitude', 1), ('gratitude', 2), ('gratitude', 3), ('gratitude', 4), ('gratitude', 5),
    ('tenderness', 1), ('tenderness', 2), ('tenderness', 3), ('tenderness', 4), ('tenderness', 5),
    ('neutral', 1), ('neutral', 2), ('neutral', 3), ('neutral', 4), ('neutral', 5)
)
update public.emotion_tags tag
set is_active = false
from public.emotions emotion
where tag.parent_emotion_id = emotion.id
  and not exists (
    select 1 from seed
    where seed.emotion = emotion.emotion and seed.display_order = tag.display_order
  );

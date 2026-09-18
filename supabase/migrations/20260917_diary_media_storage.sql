-- Private bucket used by the API service for diary image, audio, and video attachments.
insert into storage.buckets (id, name, public)
values ('diary-media', 'diary-media', false)
on conflict (id) do nothing;

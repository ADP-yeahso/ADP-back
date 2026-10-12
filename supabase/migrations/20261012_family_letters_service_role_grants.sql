-- Existing deployments may already have applied the family-letters schema
-- migration before the service_role grants were added.

grant select, insert, update, delete on public.family_letters to service_role;
grant select, insert, update, delete on public.letter_reads to service_role;
grant usage, select on sequence public.family_letters_id_seq to service_role;
grant usage, select on sequence public.letter_reads_id_seq to service_role;

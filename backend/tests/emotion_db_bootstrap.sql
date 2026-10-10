-- LOCAL disposable PostgreSQL only. Never apply this fixture to Supabase.
create role anon;
create role authenticated;
create role service_role;
create schema auth;
create table auth.users(id uuid primary key);
create function auth.uid() returns uuid language sql as $$ select null::uuid $$;

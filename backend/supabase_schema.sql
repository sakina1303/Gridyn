-- Run in the Gridyn Supabase project's SQL editor before enabling hosted mode.
-- Application requests use each user's JWT, never a service-role key.
create table if not exists public.gridyn_objects (
    owner_id uuid not null default auth.uid(),
    kind text not null,
    id uuid not null,
    payload jsonb not null,
    created_at_utc timestamptz not null default now(),
    primary key (owner_id, kind, id)
);

create index if not exists gridyn_objects_owner_kind_created
    on public.gridyn_objects (owner_id, kind, created_at_utc);

alter table public.gridyn_objects enable row level security;

create policy "Users read their own Gridyn objects"
    on public.gridyn_objects for select to authenticated
    using (owner_id = (select auth.uid()));

create policy "Users create their own Gridyn objects"
    on public.gridyn_objects for insert to authenticated
    with check (owner_id = (select auth.uid()));

create policy "Users update their own Gridyn objects"
    on public.gridyn_objects for update to authenticated
    using (owner_id = (select auth.uid()))
    with check (owner_id = (select auth.uid()));

create policy "Users delete their own Gridyn objects"
    on public.gridyn_objects for delete to authenticated
    using (owner_id = (select auth.uid()));

grant select, insert, update, delete on public.gridyn_objects to authenticated;

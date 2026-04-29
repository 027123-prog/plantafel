-- Plantafel / Betriebsapp initial schema
-- Run this in the Supabase SQL editor once for the project.

create extension if not exists pgcrypto;

create table if not exists public.employees (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  display_order integer not null default 0,
  is_apprentice boolean not null default false,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.vehicles (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  display_order integer not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.trailers (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  display_order integer not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.schedule_entries (
  id uuid primary key default gen_random_uuid(),
  legacy_id text unique,
  employee_id uuid not null references public.employees(id) on delete cascade,
  entry_date date not null,
  entry_type text not null check (
    entry_type in (
      'baustelle',
      'werkstatt',
      'werkstattkunde',
      'urlaub',
      'schule',
      'krank',
      'auto',
      'ungeklaert'
    )
  ),
  label text not null default '',
  vehicle_id uuid references public.vehicles(id) on delete set null,
  trailer_id uuid references public.trailers(id) on delete set null,
  is_workshop boolean not null default false,
  source text not null default 'plantafel',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint schedule_entries_vehicle_or_trailer_matches_auto check (
    entry_type = 'auto' or (vehicle_id is null and trailer_id is null)
  ),
  constraint schedule_entries_only_one_vehicle_or_trailer check (
    not (vehicle_id is not null and trailer_id is not null)
  )
);

create index if not exists schedule_entries_employee_date_idx
  on public.schedule_entries(employee_id, entry_date);

create index if not exists schedule_entries_date_idx
  on public.schedule_entries(entry_date);

create table if not exists public.school_patterns (
  id uuid primary key default gen_random_uuid(),
  employee_id uuid not null references public.employees(id) on delete cascade,
  weekday smallint not null check (weekday between 1 and 6),
  created_at timestamptz not null default now(),
  unique(employee_id, weekday)
);

create table if not exists public.app_documents (
  id uuid primary key default gen_random_uuid(),
  module text not null,
  title text not null,
  storage_path text not null,
  mime_type text,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now()
);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists employees_set_updated_at on public.employees;
create trigger employees_set_updated_at
before update on public.employees
for each row execute function public.set_updated_at();

drop trigger if exists vehicles_set_updated_at on public.vehicles;
create trigger vehicles_set_updated_at
before update on public.vehicles
for each row execute function public.set_updated_at();

drop trigger if exists trailers_set_updated_at on public.trailers;
create trigger trailers_set_updated_at
before update on public.trailers
for each row execute function public.set_updated_at();

drop trigger if exists schedule_entries_set_updated_at on public.schedule_entries;
create trigger schedule_entries_set_updated_at
before update on public.schedule_entries
for each row execute function public.set_updated_at();

alter table public.employees enable row level security;
alter table public.vehicles enable row level security;
alter table public.trailers enable row level security;
alter table public.schedule_entries enable row level security;
alter table public.school_patterns enable row level security;
alter table public.app_documents enable row level security;

insert into public.employees(name, display_order, is_apprentice) values
  ('MARTIN', 10, false),
  ('LUDGER', 20, false),
  ('STEPHAN', 30, false),
  ('JANNEK', 40, false),
  ('VARIS', 50, false),
  ('DAVID', 60, false),
  ('BAYAR', 70, false),
  ('TORSTEN', 80, false),
  ('FINIAN', 90, false),
  ('NOAH', 100, false),
  ('FRIEDRICH', 110, false),
  ('JONATHAN', 120, false),
  ('PATRICK', 130, false),
  ('TIMO', 140, true),
  ('GIOSUE', 150, true),
  ('ANNA', 160, true),
  ('HARALD', 170, true),
  ('KAI', 180, true),
  ('PRAKTIKANT', 190, true)
on conflict (name) do update set
  display_order = excluded.display_order,
  is_apprentice = excluded.is_apprentice,
  is_active = true;

insert into public.vehicles(name, display_order) values
  ('Sprinter Gr.', 10),
  ('Sprinter Kl.', 20),
  ('VITO', 30),
  ('CITAN', 40),
  ('FORD', 50),
  ('ALHAMBRA', 60)
on conflict (name) do update set
  display_order = excluded.display_order,
  is_active = true;

insert into public.trailers(name, display_order) values
  ('Flach', 10),
  ('Hoch', 20),
  ('Klein', 30)
on conflict (name) do update set
  display_order = excluded.display_order,
  is_active = true;

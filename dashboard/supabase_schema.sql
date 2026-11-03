-- Run only in the intended Supabase project after reviewing names and permissions.
-- CSVs in dashboard/data have identical column names to these tables.
create table if not exists public.d2_cmpd_npa_year (
  npa_id integer not null check (npa_id > 0),
  year integer not null check (year between 2017 and 2025),
  report_count bigint not null check (report_count >= 0),
  primary key (npa_id, year)
);

create table if not exists public.d2_violent_npa_year_offense (
  npa_id integer not null check (npa_id > 0),
  year integer not null check (year between 2015 and 2025),
  offense_description text not null,
  offense_level text not null check (offense_level in ('broad_category', 'specific_offense', 'injury_indicator')),
  offense_count bigint not null check (offense_count >= 0),
  primary key (npa_id, year, offense_description)
);

alter table public.d2_cmpd_npa_year enable row level security;
alter table public.d2_violent_npa_year_offense enable row level security;
revoke all on table public.d2_cmpd_npa_year from anon, authenticated;
revoke all on table public.d2_violent_npa_year_offense from anon, authenticated;
grant select on table public.d2_cmpd_npa_year to anon;
grant select on table public.d2_violent_npa_year_offense to anon;
create policy "Read D2 CMPD aggregates" on public.d2_cmpd_npa_year
  for select to anon using (true);
create policy "Read D2 violent aggregates" on public.d2_violent_npa_year_offense
  for select to anon using (true);

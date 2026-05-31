drop policy if exists "Allow source updates" on public.camera_sources;
create policy "Allow source updates"
on public.camera_sources
for update
using (true)
with check (true);

drop policy if exists "Allow source deletes" on public.camera_sources;
create policy "Allow source deletes"
on public.camera_sources
for delete
using (true);

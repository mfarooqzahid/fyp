-- Create a public Supabase Storage bucket for pre-recorded demo videos.
--
-- Use case: when the deployed system runs in the cloud (e.g., AWS ECS) and the
-- live camera infrastructure is unavailable for demonstration, video files
-- stored in this bucket can be used as stream sources. The system's stream
-- worker opens HTTP MP4 URLs through OpenCV exactly the same way it opens
-- RTSP feeds, so the demo path is identical to the production path.
--
-- Pre-recorded MP4 files are uploaded once via the Supabase dashboard or the
-- accompanying backend/upload_demo_video.py helper. Each upload produces a
-- public URL that can be pasted directly into the dashboard's "Add Source"
-- modal as the stream URL.

-- 1. Create the bucket (idempotent).
insert into storage.buckets (id, name, public)
values ('demo-videos', 'demo-videos', true)
on conflict (id) do update set public = excluded.public;

-- 2. Allow anyone to READ files from this bucket (public videos).
drop policy if exists "Public read of demo videos"
  on storage.objects;
create policy "Public read of demo videos"
  on storage.objects
  for select
  using (bucket_id = 'demo-videos');

-- 3. Allow authenticated requests (service role or signed-in users) to INSERT
--    files into this bucket. The backend's service-role key satisfies this.
drop policy if exists "Authenticated insert of demo videos"
  on storage.objects;
create policy "Authenticated insert of demo videos"
  on storage.objects
  for insert
  with check (bucket_id = 'demo-videos');

-- 4. Allow authenticated requests to UPDATE / DELETE so the helper script can
--    overwrite or clean up old demo files.
drop policy if exists "Authenticated update of demo videos"
  on storage.objects;
create policy "Authenticated update of demo videos"
  on storage.objects
  for update
  using (bucket_id = 'demo-videos')
  with check (bucket_id = 'demo-videos');

drop policy if exists "Authenticated delete of demo videos"
  on storage.objects;
create policy "Authenticated delete of demo videos"
  on storage.objects
  for delete
  using (bucket_id = 'demo-videos');

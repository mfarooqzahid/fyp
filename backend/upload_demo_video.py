"""
Upload a pre-recorded MP4 file to the Supabase Storage `demo-videos` bucket
and print the public URL ready to paste into the dashboard's Add Source modal.

Why this exists
---------------
When the system is deployed to AWS (ECS / App Runner / similar), YouTube
sources become unreliable because YouTube actively rate-limits and blocks
cloud-provider IP ranges. Pre-recorded videos uploaded once to Supabase
Storage are immune to that problem, and the stream worker opens HTTP MP4
URLs identically to RTSP feeds — same code path.

Usage
-----
    python -m backend.upload_demo_video <path-to-mp4> [--name custom-name.mp4]

Examples:
    python -m backend.upload_demo_video ./gate_entry.mp4
    python -m backend.upload_demo_video C:\\Videos\\hostel_gate.mp4 --name hostel.mp4

Prerequisites
-------------
1. The migration `202606010001_create_demo_videos_bucket.sql` has been run.
2. `SUPABASE_URL` and `SUPABASE_KEY` are set in backend/.env.
3. The supabase-py library is installed (already in requirements.txt).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Load .env first
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)
except Exception:
    pass

try:
    from supabase import Client, create_client
except Exception as exc:
    print(f"[ERROR] supabase-py not installed: {exc}")
    sys.exit(2)


BUCKET = "demo-videos"


def upload_video(file_path: Path, object_name: str | None = None) -> str:
    """Upload `file_path` to the demo-videos bucket and return its public URL."""
    if not file_path.exists():
        raise FileNotFoundError(f"Video file not found: {file_path}")
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix not in (".mp4", ".mov", ".webm", ".mkv"):
        print(f"[WARN] {suffix} may not be playable by OpenCV. Recommended: .mp4 (H.264).")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL or SUPABASE_KEY missing from backend/.env. "
            "These are required to upload to Supabase Storage."
        )

    supabase: Client = create_client(url, key)

    name = (object_name or file_path.name).strip().lstrip("/")
    print(f"[INFO] Uploading {file_path.name} ({file_path.stat().st_size / 1_000_000:.2f} MB) "
          f"to {BUCKET}/{name} ...")

    with open(file_path, "rb") as fh:
        data = fh.read()

    # Determine MIME type from extension
    mime_map = {
        ".mp4":  "video/mp4",
        ".mov":  "video/quicktime",
        ".webm": "video/webm",
        ".mkv":  "video/x-matroska",
    }
    mime = mime_map.get(suffix, "application/octet-stream")

    try:
        # supabase-py: upload returns the storage path on success.
        # `upsert=True` replaces an existing file of the same name.
        supabase.storage.from_(BUCKET).upload(
            path=name,
            file=data,
            file_options={
                "content-type": mime,
                "upsert": "true",
            },
        )
    except Exception as exc:
        # Some older client versions raise on overwrite without upsert.
        # As a fallback, try delete-then-upload.
        message = str(exc).lower()
        if "exists" in message or "duplicate" in message:
            print(f"[INFO] Object already exists; replacing it.")
            supabase.storage.from_(BUCKET).remove([name])
            supabase.storage.from_(BUCKET).upload(
                path=name,
                file=data,
                file_options={"content-type": mime},
            )
        else:
            raise

    public_url = supabase.storage.from_(BUCKET).get_public_url(name)
    if isinstance(public_url, dict):
        # newer client versions wrap the URL
        public_url = public_url.get("publicURL") or public_url.get("public_url") or str(public_url)

    return public_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload a demo video to Supabase Storage.")
    parser.add_argument("path", help="Local path to the MP4 (or .mov/.webm/.mkv) file")
    parser.add_argument("--name", help="Object name in the bucket (default: file's basename)")
    args = parser.parse_args()

    file_path = Path(args.path).expanduser().resolve()
    try:
        url = upload_video(file_path, object_name=args.name)
    except Exception as exc:
        print(f"[ERROR] Upload failed: {exc}")
        return 1

    print()
    print("=" * 72)
    print("  Upload complete.")
    print("=" * 72)
    print(f"  Public URL:")
    print(f"  {url}")
    print()
    print("  Paste this URL into the dashboard's Add Source modal:")
    print(f"    Mode:       stream")
    print(f"    Stream URL: {url}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())

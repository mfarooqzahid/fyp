from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
from urllib.parse import urlparse
from datetime import datetime, timedelta
import asyncio
import os
import sys
import json
import threading
import random

# Ensure project root and Backend on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path: sys.path.append(ROOT)
if BACKEND_DIR not in sys.path: sys.path.append(BACKEND_DIR)

try:
    from backend.analytics_engine import AnalyticsEngine
except Exception:
    # fallback import if package context differs
    try:
        from analytics_engine import AnalyticsEngine
    except Exception as e:
        AnalyticsEngine = None

try:
    from backend.source_repository import SourceRepository, SourceRepositoryError
except Exception:
    try:
        from source_repository import SourceRepository, SourceRepositoryError
    except Exception:
        SourceRepository = None
        SourceRepositoryError = Exception

try:
    from backend.db_handler import DBHandler
except Exception:
    try:
        from db_handler import DBHandler
    except Exception:
        DBHandler = None

try:
    from backend.simulator_supervisor import SimulatorSupervisor
except Exception:
    try:
        from simulator_supervisor import SimulatorSupervisor
    except Exception:
        SimulatorSupervisor = None

try:
    from backend.stream_supervisor import StreamSupervisor
except Exception:
    try:
        from stream_supervisor import StreamSupervisor
    except Exception:
        StreamSupervisor = None

app = FastAPI(title="FYP Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SOURCES_FILE = os.path.join(BACKEND_DIR, "sources.json")
_engine = None
_engine_lock = threading.Lock()
_source_repository = None
_supervisor = None
_stream_supervisor = None

class SourceCreate(BaseModel):
    title: str
    description: str
    mode: str = "generate"
    streamUrl: Optional[str] = None
    stream_url: Optional[str] = None


class SourceUpdate(BaseModel):
    title: str
    description: str
    mode: str = "generate"
    streamUrl: Optional[str] = None
    stream_url: Optional[str] = None


class SimulatorIngest(BaseModel):
    source_id: Optional[str] = None
    camera_id: str
    timestamp: Optional[str] = None
    incoming_count: int = 0
    outgoing_count: int = 0
    session_id: Optional[str] = None


@app.on_event("startup")
def startup_event():
    global _engine, _source_repository, _supervisor, _stream_supervisor
    if AnalyticsEngine is None:
        print("[WARN] AnalyticsEngine import failed; API will still serve sources but analytics endpoints will return errors.")
    else:
        with _engine_lock:
            if _engine is None:
                _engine = AnalyticsEngine()

    if SourceRepository is None:
        print("[WARN] SourceRepository import failed; source endpoints will be unavailable.")
        return

    try:
        _source_repository = SourceRepository()
    except Exception as e:
        print(f"[WARN] SourceRepository initialization failed: {e}")

    if SimulatorSupervisor is None:
        print("[WARN] SimulatorSupervisor import failed; simulator control endpoints disabled.")
    else:
        try:
            _supervisor = SimulatorSupervisor()
            _supervisor.start()
            print("[SUCCESS] Simulator supervisor started")
        except Exception as e:
            print(f"[WARN] Failed to start simulator supervisor: {e}")

    if StreamSupervisor is None:
        print("[WARN] StreamSupervisor import failed; stream control endpoints disabled.")
    else:
        try:
            _stream_supervisor = StreamSupervisor()
            _stream_supervisor.start()
            print("[SUCCESS] Stream supervisor started")
        except Exception as e:
            print(f"[WARN] Failed to start stream supervisor: {e}")


@app.on_event("shutdown")
def shutdown_event():
    global _supervisor, _stream_supervisor
    if _supervisor is not None:
        try:
            _supervisor.stop()
            print("[SUCCESS] Simulator supervisor stopped")
        except Exception as e:
            print(f"[WARN] Failed to stop simulator supervisor cleanly: {e}")
    if _stream_supervisor is not None:
        try:
            _stream_supervisor.stop()
            print("[SUCCESS] Stream supervisor stopped")
        except Exception as e:
            print(f"[WARN] Failed to stop stream supervisor cleanly: {e}")


def read_sources():
    if not os.path.exists(SOURCES_FILE):
        return []
    try:
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def write_sources(sources):
    tmp = SOURCES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2)
    os.replace(tmp, SOURCES_FILE)


def get_source_repository():
    if _source_repository is None:
        raise HTTPException(status_code=503, detail="Supabase source repository unavailable")
    return _source_repository


def get_supervisor():
    if _supervisor is None:
        raise HTTPException(status_code=503, detail="Simulator supervisor unavailable")
    return _supervisor


def get_stream_supervisor():
    if _stream_supervisor is None:
        raise HTTPException(status_code=503, detail="Stream supervisor unavailable")
    return _stream_supervisor


def attach_stream_runtime(sources):
    if _stream_supervisor is None:
        return sources

    status_by_camera = _stream_supervisor.get_status_map()
    enriched = []
    for source in sources:
        item = dict(source)
        if item.get("mode") == "stream" or item.get("source_type") == "stream":
            worker = status_by_camera.get(item.get("camera_id")) or {}
            last_status = worker.get("last_status") or {}
            worker_alive = bool(worker.get("alive"))
            item.update({
                "worker_alive": worker_alive,
                "worker_status": last_status.get("state") or ("running" if worker_alive else "stopped"),
                "last_frame_at": last_status.get("last_frame_at"),
                "last_error": last_status.get("error"),
            })
        enriched.append(item)
    return enriched


def source_mode_to_log_table(mode):
    if mode in ["stream", "live"]:
        return "live_logs"
    return "simulated_logs"


def build_rush_alerts(sources, rush_detector, minutes=10):
    alerts = []
    for source in sources:
        camera_id = (source.get("camera_id") or "").strip()
        if not camera_id:
            continue

        mode = source.get("mode") or source.get("source_type") or "generate"
        table = source_mode_to_log_table(mode)
        rush_result = rush_detector.detect_rush(camera_id, minutes=minutes, table=table)
        alerts.append({
            "source_id": source.get("id"),
            "camera_id": camera_id,
            "title": source.get("title") or camera_id,
            "mode": mode,
            "table": table,
            "status": rush_result["status"],
            "active": rush_result["is_active"],
            "current": rush_result["current"],
            "average": round(rush_result["mean"], 2),
            "ratio": round(rush_result["ratio"], 2),
            "z_score": round(rush_result["z"], 2),
            "window_minutes": rush_result["window_minutes"],
        })
    return alerts


def model_dump(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@app.get("/api/health")
def health():
    return {"status":"ok"}


@app.get("/api/sources")
def get_sources():
    try:
        return attach_stream_runtime(get_source_repository().list_sources())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sources")
def add_source(src: SourceCreate):
    payload = model_dump(src)
    title = payload.get("title", "").strip()
    description = payload.get("description", "").strip()
    mode = payload.get("mode", "generate")
    stream_url = payload.get("streamUrl") or payload.get("stream_url") or ""

    if not title:
        raise HTTPException(status_code=422, detail="Title is required")
    if not description:
        raise HTTPException(status_code=422, detail="Description is required")
    if mode not in ["generate", "stream"]:
        raise HTTPException(status_code=422, detail="Mode must be generate or stream")
    if mode == "stream" and not stream_url.strip():
        raise HTTPException(status_code=422, detail="Stream URL is required")
    if mode == "stream":
        parsed_url = urlparse(stream_url)
        # `webcam://N` is the special scheme for the host's local camera device
        # at index N (e.g. webcam://0 = default laptop webcam). The stream worker
        # converts it to an integer before handing it to cv2.VideoCapture.
        if parsed_url.scheme == "webcam":
            idx_part = (parsed_url.netloc or parsed_url.path.lstrip("/")) or "0"
            if not idx_part.isdigit():
                raise HTTPException(status_code=422, detail="Webcam URL must be webcam://0, webcam://1, etc.")
        elif parsed_url.scheme not in ["http", "https", "rtsp"] or not parsed_url.netloc:
            raise HTTPException(status_code=422, detail="Stream URL must be http, https, rtsp, or webcam://N")

    try:
        source = get_source_repository().create_source(
            title=title,
            description=description,
            mode=mode,
            stream_url=stream_url,
        )
        return {"status":"created", "source": source}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sources/{source_id}")
def delete_source(source_id: str):
    repo = get_source_repository()
    try:
        source = repo.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        camera_id = source.get("camera_id")
        mode = source.get("mode")
        
        # Stop background workers if active
        if mode == "generate" and _supervisor is not None:
            try:
                _supervisor.stop_worker(camera_id=camera_id)
            except Exception as e:
                print(f"[WARN] Failed to stop simulator worker during deletion: {e}")
        elif mode == "stream" and _stream_supervisor is not None:
            try:
                _stream_supervisor.stop_worker(camera_id=camera_id)
            except Exception as e:
                print(f"[WARN] Failed to stop stream worker during deletion: {e}")

        deleted_source = repo.delete_source(source_id)
        return {"status": "deleted", "source": deleted_source}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/sources/{source_id}")
def update_source(source_id: str, src: SourceUpdate):
    payload = model_dump(src)
    title = payload.get("title", "").strip()
    description = payload.get("description", "").strip()
    mode = payload.get("mode", "generate")
    stream_url = payload.get("streamUrl") or payload.get("stream_url") or ""

    if not title:
        raise HTTPException(status_code=422, detail="Title is required")
    if not description:
        raise HTTPException(status_code=422, detail="Description is required")
    if mode not in ["generate", "stream"]:
        raise HTTPException(status_code=422, detail="Mode must be generate or stream")
    if mode == "stream" and not stream_url.strip():
        raise HTTPException(status_code=422, detail="Stream URL is required")
    if mode == "stream":
        parsed_url = urlparse(stream_url)
        # `webcam://N` is the special scheme for the host's local camera device
        # at index N (e.g. webcam://0 = default laptop webcam). The stream worker
        # converts it to an integer before handing it to cv2.VideoCapture.
        if parsed_url.scheme == "webcam":
            idx_part = (parsed_url.netloc or parsed_url.path.lstrip("/")) or "0"
            if not idx_part.isdigit():
                raise HTTPException(status_code=422, detail="Webcam URL must be webcam://0, webcam://1, etc.")
        elif parsed_url.scheme not in ["http", "https", "rtsp"] or not parsed_url.netloc:
            raise HTTPException(status_code=422, detail="Stream URL must be http, https, rtsp, or webcam://N")

    repo = get_source_repository()
    try:
        source = repo.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        camera_id = source.get("camera_id")
        old_mode = source.get("mode")
        
        # Stop background workers for this camera so they don't run with old configs/modes
        if old_mode == "generate" and _supervisor is not None:
            try:
                _supervisor.stop_worker(camera_id=camera_id)
            except Exception as e:
                print(f"[WARN] Failed to stop simulator worker during update: {e}")
        elif old_mode == "stream" and _stream_supervisor is not None:
            try:
                _stream_supervisor.stop_worker(camera_id=camera_id)
            except Exception as e:
                print(f"[WARN] Failed to stop stream worker during update: {e}")

        updated_source = repo.update_source(
            source_id=source_id,
            title=title,
            description=description,
            mode=mode,
            stream_url=stream_url,
        )
        return {"status": "updated", "source": updated_source}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard")
def dashboard(camera: str = None, mode: str = "simulation"):
    if _engine is None:
        raise HTTPException(status_code=503, detail="AnalyticsEngine unavailable")
    cam = camera.strip() if camera and camera.strip() else None
    try:
        data = _engine.get_dashboard_data(camera_id=cam, date_val=None, hour_range=None, mode=mode)
        if data is None:
            raise HTTPException(status_code=500, detail="Analytics engine returned no data")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Small TTL cache for /api/rush-alerts so frequent polling does not hammer Supabase.
# Frontend polls every 10 s; cache TTL of 5 s halves the load while still feeling real-time.
_rush_alerts_cache = {"value": None, "ts": 0.0}
_RUSH_ALERTS_TTL_SECONDS = 5.0


@app.get("/api/rush-alerts")
def rush_alerts():
    if _engine is None:
        raise HTTPException(status_code=503, detail="AnalyticsEngine unavailable")
    try:
        import time as _time
        now = _time.monotonic()
        if (_rush_alerts_cache["value"] is not None
                and now - _rush_alerts_cache["ts"] < _RUSH_ALERTS_TTL_SECONDS):
            return _rush_alerts_cache["value"]

        sources = get_source_repository().list_sources()
        payload = {"alerts": build_rush_alerts(sources, _engine.rush)}
        _rush_alerts_cache["value"] = payload
        _rush_alerts_cache["ts"] = now
        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/camera_comparison")
def camera_comparison(mode: str = "simulation"):
    if _engine is None:
        raise HTTPException(status_code=503, detail="AnalyticsEngine unavailable")
    try:
        return _engine.get_camera_comparison(mode=mode)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/frame")
def frame(camera: Optional[str] = None):
    if camera and camera.strip():
        safe_camera = os.path.basename(camera.strip())
        frame_path = os.path.join(BACKEND_DIR, "frames", f"{safe_camera}.jpg")
        if os.path.exists(frame_path):
            return FileResponse(frame_path, media_type="image/jpeg")
        raise HTTPException(status_code=404, detail="Frame not available")

    frame_path = os.path.join(BACKEND_DIR, "current_frame.jpg")
    if os.path.exists(frame_path):
        return FileResponse(frame_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Frame not available")


# MJPEG continuous live stream for a single camera.
#
# Browsers natively render `multipart/x-mixed-replace` via an <img> tag — no
# JavaScript polling needed. Each time the stream worker writes a new annotated
# JPEG to backend/frames/{camera_id}.jpg, we push it as the next multipart part.
# This replaces the previous 500 ms JPEG-polling loop, which felt like a
# slideshow even on a fast network.
RECORDINGS_DIR = os.path.join(BACKEND_DIR, "recordings")


def _safe_camera_dir(camera_id: str):
    """Return the absolute, sandboxed recording directory for a camera, or None."""
    safe = os.path.basename((camera_id or "").strip())
    if not safe:
        return None
    candidate = os.path.realpath(os.path.join(RECORDINGS_DIR, safe))
    base_real = os.path.realpath(RECORDINGS_DIR)
    # Prevent path traversal: candidate must live inside RECORDINGS_DIR.
    if not candidate.startswith(base_real + os.sep) and candidate != base_real:
        return None
    return candidate


def _list_camera_chunks(camera_id: str, since_ts: float = 0.0):
    """List recorded MP4 chunks for a camera as
    [{'start_ts': float, 'end_ts': float, 'path': str, 'size': int}, ...]
    sorted by start_ts ascending. `start_ts` is parsed from the filename
    (HHMMSS) combined with the day folder (YYYYMMDD)."""
    cam_dir = _safe_camera_dir(camera_id)
    if not cam_dir or not os.path.isdir(cam_dir):
        return []
    chunks = []
    for day_name in sorted(os.listdir(cam_dir)):
        day_dir = os.path.join(cam_dir, day_name)
        if not os.path.isdir(day_dir) or len(day_name) != 8 or not day_name.isdigit():
            continue
        try:
            day_date = datetime.strptime(day_name, "%Y%m%d")
        except ValueError:
            continue
        for entry in sorted(os.listdir(day_dir)):
            if not entry.endswith(".mp4"):
                continue
            time_part = entry[:-4]
            if len(time_part) != 6 or not time_part.isdigit():
                continue
            try:
                start_dt = day_date.replace(
                    hour=int(time_part[0:2]),
                    minute=int(time_part[2:4]),
                    second=int(time_part[4:6]),
                )
            except ValueError:
                continue
            full = os.path.join(day_dir, entry)
            try:
                size = os.path.getsize(full)
                mtime = os.path.getmtime(full)
            except OSError:
                continue
            start_ts = start_dt.timestamp()
            # End time = file mtime (when last frame was written). Falls back to
            # start + a nominal chunk length if mtime <= start (unfinished file).
            end_ts = mtime if mtime > start_ts else start_ts + 60.0
            if start_ts < since_ts and end_ts < since_ts:
                continue
            chunks.append({
                "start_ts": start_ts,
                "end_ts": end_ts,
                "path": full,
                "size": size,
            })
    chunks.sort(key=lambda c: c["start_ts"])
    return chunks


def _parse_playback_time(value: str):
    """Accept ISO datetime, HH:MM, or HH:MM:SS; return a unix timestamp."""
    if not value:
        return None
    value = value.strip()
    # Full ISO 8601 / datetime-local string
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt.timestamp()
    except ValueError:
        pass
    # Bare HH:MM[:SS] → assume today
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            t = datetime.strptime(value, fmt).time()
            today = datetime.now().date()
            return datetime.combine(today, t).timestamp()
        except ValueError:
            continue
    return None


@app.get("/api/playback/{camera_id}/timeline")
def playback_timeline(camera_id: str, hours: int = 6):
    """Return the list of available recorded chunks for a camera.

    Used by the dashboard timeline slider to know which time-ranges are
    playable. Each chunk is represented by ISO start/end and a `clip_url`
    suitable for an HTML <video> src.
    """
    hours = max(1, min(int(hours or 6), 48))
    since_ts = (datetime.now() - timedelta(hours=hours)).timestamp()
    chunks = _list_camera_chunks(camera_id, since_ts=since_ts)
    return {
        "camera_id": camera_id,
        "window_hours": hours,
        "now_iso": datetime.now().astimezone().isoformat(),
        "chunks": [
            {
                "start_iso": datetime.fromtimestamp(c["start_ts"]).astimezone().isoformat(),
                "end_iso": datetime.fromtimestamp(c["end_ts"]).astimezone().isoformat(),
                "start_ts": c["start_ts"],
                "end_ts": c["end_ts"],
                "size": c["size"],
                "clip_url": f"/api/playback/{camera_id}/clip?ts={c['start_ts']:.0f}",
            }
            for c in chunks
        ],
    }


@app.get("/api/playback/{camera_id}/clip")
def playback_clip(camera_id: str, time: Optional[str] = None, ts: Optional[float] = None):
    """Serve the MP4 chunk covering the requested timestamp.

    Accepts either `?ts=<unix_seconds>` (preferred, what the timeline endpoint
    returns) or `?time=<HH:MM | HH:MM:SS | ISO>` for direct user URLs.
    Returns the chunk whose [start, end] window contains the requested time;
    if none exactly contains it, returns the nearest chunk.
    FileResponse handles HTTP Range so the <video> element can seek.
    """
    target_ts = None
    if ts is not None:
        try:
            target_ts = float(ts)
        except (TypeError, ValueError):
            target_ts = None
    if target_ts is None and time:
        target_ts = _parse_playback_time(time)
    if target_ts is None:
        raise HTTPException(status_code=422, detail="Provide ?ts=<unix> or ?time=<HH:MM>")

    chunks = _list_camera_chunks(camera_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="No recordings available for this camera")

    # Prefer a chunk whose window contains the target; else closest by start.
    chosen = None
    for c in chunks:
        if c["start_ts"] <= target_ts <= c["end_ts"]:
            chosen = c
            break
    if chosen is None:
        chosen = min(chunks, key=lambda c: abs(c["start_ts"] - target_ts))

    if not os.path.exists(chosen["path"]):
        raise HTTPException(status_code=404, detail="Chunk file missing")
    return FileResponse(
        chosen["path"],
        media_type="video/mp4",
        headers={
            "X-Chunk-Start": str(chosen["start_ts"]),
            "X-Chunk-End": str(chosen["end_ts"]),
            "Cache-Control": "public, max-age=60",
        },
    )


@app.get("/api/webcams")
def list_webcams(max_index: int = 5):
    """Probe local camera device indices and report which ones are available.

    Useful diagnostic — before registering `webcam://N`, hit this endpoint to
    discover which N values map to real devices on this host.
    Tries cv2.VideoCapture(i) for i in [0, max_index] and reports which open
    and what frame size they produce.
    """
    try:
        import cv2  # local import: keeps base API import cheap if opencv missing
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"OpenCV unavailable: {exc}")

    max_index = max(0, min(int(max_index or 5), 10))
    results = []
    for idx in range(max_index + 1):
        info = {"index": idx, "url": f"webcam://{idx}", "available": False,
                "width": None, "height": None, "error": None}
        cap = None
        try:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    info["available"] = True
                    info["height"], info["width"] = frame.shape[:2]
                else:
                    info["error"] = "opened but no frame returned"
            else:
                info["error"] = "device not present"
        except Exception as exc:
            info["error"] = str(exc)
        finally:
            if cap is not None:
                try: cap.release()
                except Exception: pass
        results.append(info)
    return {"cameras": results}


@app.get("/api/stream/{camera_id}")
async def stream_mjpeg(camera_id: str, request: Request):
    safe_camera = os.path.basename(camera_id.strip())
    if not safe_camera:
        raise HTTPException(status_code=422, detail="camera_id is required")
    frame_path = os.path.join(BACKEND_DIR, "frames", f"{safe_camera}.jpg")

    async def generator():
        last_mtime = 0.0
        idle_since = None
        # Quick "no signal" placeholder bytes (tiny grey JPEG) so the client
        # always gets *something* on connect, even before the worker has
        # written the first frame.
        loop = asyncio.get_event_loop()
        while True:
            if await request.is_disconnected():
                break
            try:
                if not os.path.exists(frame_path):
                    if idle_since is None:
                        idle_since = loop.time()
                    elif loop.time() - idle_since > 30:
                        # Worker has been quiet for 30 s — let the client
                        # reconnect (the browser does this automatically).
                        break
                    await asyncio.sleep(0.2)
                    continue

                mtime = os.path.getmtime(frame_path)
                if mtime != last_mtime:
                    try:
                        with open(frame_path, "rb") as f:
                            data = f.read()
                    except OSError:
                        await asyncio.sleep(0.05)
                        continue
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n"
                        + data + b"\r\n"
                    )
                    last_mtime = mtime
                    idle_since = None
                else:
                    # No new frame yet — poll the file at ~20 Hz so we push
                    # the next frame within ~50 ms of the worker writing it.
                    await asyncio.sleep(0.05)
            except (asyncio.CancelledError, GeneratorExit):
                break
            except Exception as exc:
                print(f"[MJPEG] stream {safe_camera} error: {exc}")
                break

    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "X-Accel-Buffering": "no",  # disable buffering when behind nginx
    }
    return StreamingResponse(
        generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers=headers,
    )


@app.get("/api/camera/{camera_id}/occupancy")
def get_occupancy(camera_id: str, start_hour: int = 8, end_hour: int = 17, mode: str = "simulation"):
    """
    Get occupancy data for a camera within a time range.
    
    Args:
        camera_id: Camera ID to fetch data for
        start_hour: Start hour of the day (0-23, default 8 for 8am)
        end_hour: End hour of the day (0-23, default 17 for 5pm)
        mode: Data mode - 'simulation', 'simulated', 'live', or 'audit'
    
    Returns:
        {
            "camera_id": str,
            "incoming_count": int,
            "outgoing_count": int,
            "current_occupancy": int,
            "last_updated": str (ISO format),
            "mode": str
        }
    """
    if _engine is None:
        raise HTTPException(status_code=503, detail="AnalyticsEngine unavailable")
    
    if mode not in ["simulation", "simulated", "live", "audit"]:
        raise HTTPException(status_code=422, detail="Mode must be simulation, simulated, live, or audit")
    
    try:
        # Map mode to table name
        table_map = {
            "simulation": "simulated_logs",
            "simulated": "simulated_logs",
            "live": "live_logs",
            "audit": "audit_logs"
        }
        table = table_map[mode]
        
        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Define time range (8am to 5pm today)
        hours_range = (start_hour, end_hour)
        
        # Use analytics service to get counts
        incoming = _engine.shared_service.get_total_visitors(
            camera_id=camera_id,
            direction='IN',
            date=today,
            hours=hours_range,
            table=table
        )
        
        outgoing = _engine.shared_service.get_total_visitors(
            camera_id=camera_id,
            direction='OUT',
            date=today,
            hours=hours_range,
            table=table
        )
        
        occupancy = max(0, incoming - outgoing)
        
        return {
            "camera_id": camera_id,
            "incoming_count": incoming,
            "outgoing_count": outgoing,
            "current_occupancy": occupancy,
            "last_updated": datetime.now().isoformat(),
            "mode": mode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulator/ingest")
def ingest_simulator_counts(payload: SimulatorIngest):
    if DBHandler is None:
        raise HTTPException(status_code=503, detail="DBHandler unavailable")

    camera_id = payload.camera_id.strip()
    if not camera_id:
        raise HTTPException(status_code=422, detail="camera_id is required")

    incoming = max(0, int(payload.incoming_count))
    outgoing = max(0, int(payload.outgoing_count))
    total = incoming + outgoing

    if total == 0:
        return {
            "status": "ok",
            "camera_id": camera_id,
            "inserted_rows": 0,
            "session_id": payload.session_id or "simulated",
        }

    frame_seed = int(datetime.now().timestamp())
    session_id = payload.session_id or f"SIM_{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    db = DBHandler(camera_id=camera_id)
    try:
        inserted = 0
        for _ in range(incoming):
            tid = random.randint(100000, 999999)
            db.insert_detection(
                track_id=tid,
                obj_class="person",
                confidence=1.0,
                bbox=(0, 0, 1, 1),
                frame_number=frame_seed,
                direction="IN",
                session_id=session_id,
                table="simulated_logs",
            )
            inserted += 1

        for _ in range(outgoing):
            tid = random.randint(100000, 999999)
            db.insert_detection(
                track_id=tid,
                obj_class="person",
                confidence=1.0,
                bbox=(0, 0, 1, 1),
                frame_number=frame_seed,
                direction="OUT",
                session_id=session_id,
                table="simulated_logs",
            )
            inserted += 1

        return {
            "status": "ok",
            "camera_id": camera_id,
            "inserted_rows": inserted,
            "session_id": session_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/simulator/workers")
def simulator_workers():
    try:
        return {"workers": get_supervisor().list_workers()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulator/start/{camera_id}")
def simulator_start(camera_id: str):
    try:
        return get_supervisor().start_worker(camera_id=camera_id, source_id=camera_id, managed=False)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulator/stop/{camera_id}")
def simulator_stop(camera_id: str):
    try:
        return get_supervisor().stop_worker(camera_id=camera_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulator/restart/{camera_id}")
def simulator_restart(camera_id: str):
    try:
        return get_supervisor().restart_worker(camera_id=camera_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stream/workers")
def stream_workers():
    try:
        return {"workers": get_stream_supervisor().list_workers()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream/start/{camera_id}")
def stream_start(camera_id: str):
    try:
        return get_stream_supervisor().start_worker(camera_id=camera_id, managed=False)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream/stop/{camera_id}")
def stream_stop(camera_id: str):
    try:
        return get_stream_supervisor().stop_worker(camera_id=camera_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream/restart/{camera_id}")
def stream_restart(camera_id: str):
    try:
        return get_stream_supervisor().restart_worker(camera_id=camera_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

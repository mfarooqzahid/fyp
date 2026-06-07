import os
import time
from datetime import datetime

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

try:
    from backend.config import (
        DEEPSORT_MAX_AGE as _CFG_DEEPSORT_MAX_AGE,
        MODEL_PATH,
        STREAM_YOLO_CONF as _CFG_STREAM_YOLO_CONF,
        STREAM_IN_DEBOUNCE_SECONDS as _CFG_STREAM_IN_DEBOUNCE_SECONDS,
        STREAM_TRACK_MISS_TOLERANCE_FRAMES as _CFG_STREAM_TRACK_MISS_TOLERANCE_FRAMES,
        STREAM_MIN_TRACK_DISPLACEMENT_PX as _CFG_STREAM_MIN_TRACK_DISPLACEMENT_PX,
        STREAM_CLAHE_ENABLED as _CFG_STREAM_CLAHE_ENABLED,
        STREAM_CLAHE_CLIP_LIMIT as _CFG_STREAM_CLAHE_CLIP_LIMIT,
        STREAM_CLAHE_TILE_GRID as _CFG_STREAM_CLAHE_TILE_GRID,
        STREAM_MIN_BBOX_HEIGHT_PX as _CFG_STREAM_MIN_BBOX_HEIGHT_PX,
        STREAM_MAX_BBOX_HEIGHT_RATIO as _CFG_STREAM_MAX_BBOX_HEIGHT_RATIO,
        STREAM_RECORDING_ENABLED as _CFG_STREAM_RECORDING_ENABLED,
        STREAM_RECORDING_CHUNK_SECONDS as _CFG_STREAM_RECORDING_CHUNK_SECONDS,
        STREAM_RECORDING_RETENTION_HOURS as _CFG_STREAM_RECORDING_RETENTION_HOURS,
        STREAM_LINE_CROSSING_ENABLED as _CFG_STREAM_LINE_CROSSING_ENABLED,
        STREAM_LINE_ORIENTATION as _CFG_STREAM_LINE_ORIENTATION,
        STREAM_LINE_POSITION as _CFG_STREAM_LINE_POSITION,
        STREAM_LINE_IN_SIDE as _CFG_STREAM_LINE_IN_SIDE,
    )
except Exception:
    from config import (
        DEEPSORT_MAX_AGE as _CFG_DEEPSORT_MAX_AGE,
        MODEL_PATH,
        STREAM_YOLO_CONF as _CFG_STREAM_YOLO_CONF,
        STREAM_IN_DEBOUNCE_SECONDS as _CFG_STREAM_IN_DEBOUNCE_SECONDS,
        STREAM_TRACK_MISS_TOLERANCE_FRAMES as _CFG_STREAM_TRACK_MISS_TOLERANCE_FRAMES,
        STREAM_MIN_TRACK_DISPLACEMENT_PX as _CFG_STREAM_MIN_TRACK_DISPLACEMENT_PX,
        STREAM_CLAHE_ENABLED as _CFG_STREAM_CLAHE_ENABLED,
        STREAM_CLAHE_CLIP_LIMIT as _CFG_STREAM_CLAHE_CLIP_LIMIT,
        STREAM_CLAHE_TILE_GRID as _CFG_STREAM_CLAHE_TILE_GRID,
        STREAM_MIN_BBOX_HEIGHT_PX as _CFG_STREAM_MIN_BBOX_HEIGHT_PX,
        STREAM_MAX_BBOX_HEIGHT_RATIO as _CFG_STREAM_MAX_BBOX_HEIGHT_RATIO,
        STREAM_RECORDING_ENABLED as _CFG_STREAM_RECORDING_ENABLED,
        STREAM_RECORDING_CHUNK_SECONDS as _CFG_STREAM_RECORDING_CHUNK_SECONDS,
        STREAM_RECORDING_RETENTION_HOURS as _CFG_STREAM_RECORDING_RETENTION_HOURS,
        STREAM_LINE_CROSSING_ENABLED as _CFG_STREAM_LINE_CROSSING_ENABLED,
        STREAM_LINE_ORIENTATION as _CFG_STREAM_LINE_ORIENTATION,
        STREAM_LINE_POSITION as _CFG_STREAM_LINE_POSITION,
        STREAM_LINE_IN_SIDE as _CFG_STREAM_LINE_IN_SIDE,
    )


BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR = os.path.join(BACKEND_DIR, "frames")
RECORDINGS_DIR = os.path.join(BACKEND_DIR, "recordings")
STREAM_PROCESS_INTERVAL_SECONDS = float(os.getenv("STREAM_PROCESS_INTERVAL_SECONDS", "0.5"))
STREAM_MAX_FRAME_WIDTH = int(os.getenv("STREAM_MAX_FRAME_WIDTH", "960"))
STREAM_JPEG_INTERVAL_SECONDS = float(os.getenv("STREAM_JPEG_INTERVAL_SECONDS", "0.5"))
STREAM_YOLO_IMGSZ = int(os.getenv("STREAM_YOLO_IMGSZ", "640"))
STREAM_YOLO_CONF = float(os.getenv("STREAM_YOLO_CONF", str(_CFG_STREAM_YOLO_CONF)))
STREAM_IN_DEBOUNCE_SECONDS = float(os.getenv("STREAM_IN_DEBOUNCE_SECONDS", str(_CFG_STREAM_IN_DEBOUNCE_SECONDS)))
STREAM_TRACK_MISS_TOLERANCE_FRAMES = int(os.getenv("STREAM_TRACK_MISS_TOLERANCE_FRAMES", str(_CFG_STREAM_TRACK_MISS_TOLERANCE_FRAMES)))
STREAM_CLAHE_ENABLED = os.getenv("STREAM_CLAHE_ENABLED", str(_CFG_STREAM_CLAHE_ENABLED)).strip().lower() in ("1", "true", "yes", "on")
STREAM_CLAHE_CLIP_LIMIT = float(os.getenv("STREAM_CLAHE_CLIP_LIMIT", str(_CFG_STREAM_CLAHE_CLIP_LIMIT)))
STREAM_CLAHE_TILE_GRID = int(os.getenv("STREAM_CLAHE_TILE_GRID", str(_CFG_STREAM_CLAHE_TILE_GRID)))
STREAM_MIN_BBOX_HEIGHT_PX = int(os.getenv("STREAM_MIN_BBOX_HEIGHT_PX", str(_CFG_STREAM_MIN_BBOX_HEIGHT_PX)))
STREAM_MAX_BBOX_HEIGHT_RATIO = float(os.getenv("STREAM_MAX_BBOX_HEIGHT_RATIO", str(_CFG_STREAM_MAX_BBOX_HEIGHT_RATIO)))
DEEPSORT_MAX_AGE = int(os.getenv("DEEPSORT_MAX_AGE", str(_CFG_DEEPSORT_MAX_AGE)))
STREAM_MIN_TRACK_DISPLACEMENT_PX = int(os.getenv("STREAM_MIN_TRACK_DISPLACEMENT_PX", str(_CFG_STREAM_MIN_TRACK_DISPLACEMENT_PX)))
STREAM_LINE_CROSSING_ENABLED = os.getenv("STREAM_LINE_CROSSING_ENABLED", str(_CFG_STREAM_LINE_CROSSING_ENABLED)).strip().lower() in ("1", "true", "yes", "on")
STREAM_LINE_ORIENTATION = os.getenv("STREAM_LINE_ORIENTATION", str(_CFG_STREAM_LINE_ORIENTATION)).strip().lower()
STREAM_LINE_POSITION = float(os.getenv("STREAM_LINE_POSITION", str(_CFG_STREAM_LINE_POSITION)))
STREAM_LINE_IN_SIDE = os.getenv("STREAM_LINE_IN_SIDE", str(_CFG_STREAM_LINE_IN_SIDE)).strip().lower()
STREAM_RECORDING_ENABLED = os.getenv("STREAM_RECORDING_ENABLED", str(_CFG_STREAM_RECORDING_ENABLED)).strip().lower() in ("1", "true", "yes", "on")
STREAM_RECORDING_CHUNK_SECONDS = int(os.getenv("STREAM_RECORDING_CHUNK_SECONDS", str(_CFG_STREAM_RECORDING_CHUNK_SECONDS)))
STREAM_RECORDING_RETENTION_HOURS = int(os.getenv("STREAM_RECORDING_RETENTION_HOURS", str(_CFG_STREAM_RECORDING_RETENTION_HOURS)))


def is_track_visible(track):
    """Return True only when DeepSORT updated this track from the current frame."""
    return getattr(track, "time_since_update", 0) == 0


def is_track_recently_seen(track, tolerance_frames=STREAM_TRACK_MISS_TOLERANCE_FRAMES):
    """Track counts as 'present' if DeepSORT updated it within the last N frames.

    Tolerating brief detection misses prevents a momentary occlusion from
    firing OUT immediately followed by IN when the same person reappears.
    """
    return getattr(track, "time_since_update", 0) <= tolerance_frames


def get_presence_events(previous_active_ids, current_active_ids):
    return {
        "incoming": set(current_active_ids) - set(previous_active_ids),
        "outgoing": set(previous_active_ids) - set(current_active_ids),
    }


def resize_for_detection(frame, max_width):
    if not max_width or max_width <= 0:
        return frame

    height, width = frame.shape[:2]
    if width <= max_width:
        return frame

    scale = max_width / width
    return __import__("cv2").resize(frame, (max_width, int(height * scale)))


def apply_clahe(frame, clip_limit=STREAM_CLAHE_CLIP_LIMIT, tile_grid=STREAM_CLAHE_TILE_GRID):
    """Boost local contrast on the luminance channel.

    Operates in LAB space so colour is preserved. Lightweight (~2-3 ms on a
    960px-wide frame) and helps YOLO catch people in low-light or
    backlit scenes.
    """
    cv2 = __import__("cv2")
    if frame is None or frame.size == 0:
        return frame
    if len(frame.shape) == 2:
        # already single-channel grayscale
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid))
        return clahe.apply(frame)
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid))
    l_eq = clahe.apply(l)
    lab_eq = cv2.merge((l_eq, a, b))
    return cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)


def is_bbox_size_valid(bbox_xywh, frame_height,
                       min_height_px=STREAM_MIN_BBOX_HEIGHT_PX,
                       max_height_ratio=STREAM_MAX_BBOX_HEIGHT_RATIO):
    """Reject detections that are too small or absurdly large.

    bbox_xywh is [x, y, w, h] in pixels on the detection frame.
    """
    _, _, _, h = bbox_xywh
    if h < min_height_px:
        return False
    if frame_height > 0 and (h / frame_height) > max_height_ratio:
        return False
    return True


def compute_line_pixel(frame_w, frame_h, orientation, position_fraction):
    """Convert a (orientation, fractional position) line into a pixel coord.

    For 'horizontal' we return the y-pixel; for 'vertical' the x-pixel.
    """
    frac = max(0.05, min(0.95, float(position_fraction or 0.5)))
    if orientation == "vertical":
        return int(round(frame_w * frac))
    return int(round(frame_h * frac))


def determine_side(center_xy, orientation, line_pixel):
    """Return which side of the counting line the center point is on.

    Horizontal line: 'above' (cy < line) or 'below' (cy >= line).
    Vertical line:   'left'  (cx < line) or 'right' (cx >= line).
    """
    cx, cy = center_xy
    if orientation == "vertical":
        return "left" if cx < line_pixel else "right"
    return "above" if cy < line_pixel else "below"


def crossing_direction(prev_side, curr_side, orientation, in_side):
    """Decide IN / OUT / None for a side transition.

    in_side names which side of the line is the "IN" zone. Crossing INTO that
    side fires IN, crossing OUT of it fires OUT. Same-side returns None.
    """
    if prev_side is None or prev_side == curr_side:
        return None
    if orientation == "horizontal":
        in_target = "below" if in_side in ("down", "below", "bottom") else "above"
    else:
        in_target = "right" if in_side in ("right", "east") else "left"
    if curr_side == in_target:
        return "IN"
    if prev_side == in_target:
        return "OUT"
    return None


class ChunkRecorder:
    """Write annotated frames into rolling N-second MP4 chunks per camera.

    Files live at: <RECORDINGS_DIR>/<camera_id>/<YYYYMMDD>/<HHMMSS>.mp4
    Older files beyond the retention window are pruned on each rollover.

    Codec is `mp4v` (MPEG-4 Part 2) — it ships with stock opencv-python on
    every platform we care about and plays natively in Chrome / Firefox / Edge
    via the HTML <video> element. Quality is fine for surveillance footage.
    """

    def __init__(self, camera_id, fps, chunk_seconds, retention_hours,
                 base_dir=RECORDINGS_DIR):
        self.camera_id = os.path.basename((camera_id or "").strip()) or "unknown"
        self.fps = max(1.0, float(fps))
        self.chunk_seconds = max(5, int(chunk_seconds))
        self.retention_seconds = max(60, int(retention_hours) * 3600)
        self.base_dir = base_dir
        self.camera_dir = os.path.join(self.base_dir, self.camera_id)
        os.makedirs(self.camera_dir, exist_ok=True)

        self._writer = None
        self._writer_path = None
        self._writer_started_at = None  # monotonic
        self._writer_size = None        # (w, h) the writer was opened with
        self._last_cleanup_at = 0.0     # monotonic

    def _open_writer(self, frame_size):
        cv2 = __import__("cv2")
        now = datetime.now()
        day_dir = os.path.join(self.camera_dir, now.strftime("%Y%m%d"))
        os.makedirs(day_dir, exist_ok=True)
        path = os.path.join(day_dir, now.strftime("%H%M%S") + ".mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(path, fourcc, self.fps, frame_size)
        if not writer.isOpened():
            try:
                writer.release()
            except Exception:
                pass
            return None, None
        return writer, path

    def write(self, frame):
        if frame is None or frame.size == 0:
            return
        h, w = frame.shape[:2]
        frame_size = (int(w), int(h))
        now_mono = time.monotonic()

        # Rollover when chunk window elapsed or frame size changed.
        rollover = (
            self._writer is None
            or self._writer_size != frame_size
            or (self._writer_started_at is not None
                and now_mono - self._writer_started_at >= self.chunk_seconds)
        )
        if rollover:
            self._close_writer()
            writer, path = self._open_writer(frame_size)
            if writer is None:
                # Skip recording this frame; try again on next write.
                return
            self._writer = writer
            self._writer_path = path
            self._writer_started_at = now_mono
            self._writer_size = frame_size

        try:
            self._writer.write(frame)
        except Exception as exc:
            # Don't kill the worker on a single bad write; try to recover next frame.
            print(f"[RECORDER] {self.camera_id} write failed: {exc}")
            self._close_writer()
            return

        # Periodic cleanup of old chunks (once per ~chunk_seconds).
        if now_mono - self._last_cleanup_at >= self.chunk_seconds:
            self._last_cleanup_at = now_mono
            try:
                self._prune_old_chunks()
            except Exception as exc:
                print(f"[RECORDER] {self.camera_id} cleanup failed: {exc}")

    def _close_writer(self):
        if self._writer is not None:
            try:
                self._writer.release()
            except Exception:
                pass
        self._writer = None
        self._writer_path = None
        self._writer_started_at = None
        self._writer_size = None

    def _prune_old_chunks(self):
        cutoff = time.time() - self.retention_seconds
        if not os.path.isdir(self.camera_dir):
            return
        for day_name in os.listdir(self.camera_dir):
            day_dir = os.path.join(self.camera_dir, day_name)
            if not os.path.isdir(day_dir):
                continue
            for entry in os.listdir(day_dir):
                if not entry.endswith(".mp4"):
                    continue
                full = os.path.join(day_dir, entry)
                try:
                    if os.path.getmtime(full) < cutoff:
                        os.remove(full)
                except OSError:
                    pass
            # Remove empty day directories.
            try:
                if not os.listdir(day_dir):
                    os.rmdir(day_dir)
            except OSError:
                pass

    def close(self):
        self._close_writer()


def _status(status_queue, **payload):
    try:
        status_queue.put(payload)
    except Exception:
        pass


def run_stream_worker(camera_id, source_id, stream_url, stop_event, status_queue):
    """Read one stream URL, count frame presence, and persist IN/OUT events to live_logs."""
    session_id = f"LIVE_{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    started_at = datetime.now().astimezone().isoformat()

    try:
        import cv2
        cv2.setNumThreads(1)
        try:
            from backend.db_handler import DBHandler
        except Exception:
            from db_handler import DBHandler
        from deep_sort_realtime.deepsort_tracker import DeepSort
        try:
            import torch
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
        except Exception:
            pass
        from ultralytics import YOLO
    except Exception as exc:
        _status(
            status_queue,
            camera_id=camera_id,
            source_id=source_id,
            stream_url=stream_url,
            session_id=session_id,
            started_at=started_at,
            ok=False,
            state="dependency_error",
            error=f"Stream dependencies unavailable: {exc}",
            last_frame_at=None,
            inserted_rows=0,
        )
        return

    os.makedirs(FRAMES_DIR, exist_ok=True)
    frame_path = os.path.join(FRAMES_DIR, f"{camera_id}.jpg")
    active_track_ids = set()              # tracks already logged as IN (not yet OUT)
    pending_in_since = {}                  # track_id -> monotonic time first seen
    last_bbox_by_track = {}
    # Displacement tracking: stationary detections (chairs, posters, shadows
    # mis-labelled as person) never accumulate real movement; we refuse to log
    # them as IN even after the time debounce passes.
    track_first_center = {}                # track_id -> (cx, cy) at first sighting
    track_max_displacement = {}            # track_id -> max(distance from first_center)
    # Line-crossing state. A track contributes at most one IN and one OUT event
    # per direction over its lifetime — eliminates the over-counting that
    # presence-based logic produces when YOLO loses+regains the same person.
    track_side = {}                        # track_id -> "above"/"below"/"left"/"right"
    track_crossed_directions = {}          # track_id -> set of {"IN","OUT"} already fired
    frame_count = 0
    inserted_rows = 0
    current_occupancy = 0
    last_processed_at = 0
    last_jpeg_at = 0

    recorder = None
    if STREAM_RECORDING_ENABLED:
        try:
            # Playback FPS matches the rate at which we actually push annotated
            # frames into the chunk file. STREAM_PROCESS_INTERVAL_SECONDS=0.5
            # yields 2 fps; bump it (lower the interval) for smoother playback.
            recording_fps = 1.0 / max(STREAM_PROCESS_INTERVAL_SECONDS, 0.05)
            recorder = ChunkRecorder(
                camera_id=camera_id,
                fps=recording_fps,
                chunk_seconds=STREAM_RECORDING_CHUNK_SECONDS,
                retention_hours=STREAM_RECORDING_RETENTION_HOURS,
            )
        except Exception as exc:
            print(f"[RECORDER] init failed for {camera_id}: {exc}")
            recorder = None

    model = tracker = db = cap = None
    try:
        model = YOLO(MODEL_PATH)
        tracker = DeepSort(max_age=DEEPSORT_MAX_AGE)
        db = DBHandler(camera_id=camera_id)
        
        # Detect special source types before opening capture.
        # `webcam://N` → opens local camera device N (e.g. laptop built-in webcam at 0)
        # YouTube → uses yt_dlp to resolve to a direct media URL
        # Everything else → opened as a generic URL string (RTSP, HTTP MJPEG, file, etc.)
        is_webcam = stream_url.lower().startswith("webcam://")
        webcam_index = None
        if is_webcam:
            from urllib.parse import urlparse as _urlparse
            parsed = _urlparse(stream_url)
            idx_part = (parsed.netloc or parsed.path.lstrip("/")) or "0"
            try:
                webcam_index = int(idx_part)
            except ValueError:
                webcam_index = 0
            actual_url = webcam_index  # cv2.VideoCapture accepts int for local devices
            is_youtube = False
        else:
            is_youtube = "youtube.com" in stream_url.lower() or "youtu.be" in stream_url.lower()
            if is_youtube:
                try:
                    import yt_dlp
                    ydl_opts = {
                        "format": "best[ext=mp4]/best",
                        "quiet": True,
                        "no_warnings": True,
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(stream_url, download=False)
                        actual_url = info.get('url') or stream_url
                except Exception as e:
                    print(f"[ERROR] Failed to extract YouTube stream in stream_worker: {e}")
                    actual_url = stream_url
            else:
                actual_url = stream_url

        cap = cv2.VideoCapture(actual_url)

        if not cap.isOpened():
            _status(
                status_queue,
                camera_id=camera_id,
                source_id=source_id,
                stream_url=stream_url,
                session_id=session_id,
                started_at=started_at,
                ok=False,
                state="open_failed",
                error=f"Unable to open stream URL: {stream_url}",
                last_frame_at=None,
                inserted_rows=0,
            )
            return

        _status(
            status_queue,
            camera_id=camera_id,
            source_id=source_id,
            stream_url=stream_url,
            session_id=session_id,
            started_at=started_at,
            ok=True,
            state="running",
            error=None,
            last_frame_at=None,
            inserted_rows=0,
        )

        while not stop_event.is_set():
            loop_started_at = time.monotonic()
            ret, frame = cap.read()
            if not ret:
                print(f"[STREAM LOOP] Stream ended or frame read failed. Rewinding connection for continuous playback...")
                # 1. Try to seek to frame 0 first (fastest for files)
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                
                # 2. If seeking fails (typical for network/YouTube/webcam streams), re-initialize the VideoCapture
                if not ret:
                    cap.release()
                    if is_webcam:
                        actual_url = webcam_index  # re-open the same local device
                    elif is_youtube:
                        try:
                            import yt_dlp
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                info = ydl.extract_info(stream_url, download=False)
                                actual_url = info.get('url') or stream_url
                        except Exception as e:
                            print(f"[STREAM LOOP ERROR] Failed to re-extract YouTube stream: {e}")
                            actual_url = stream_url
                    else:
                        actual_url = stream_url

                    cap = cv2.VideoCapture(actual_url)
                    ret, frame = cap.read()
                
                # 3. If it STILL fails, only then we stop
                if not ret:
                    _status(
                        status_queue,
                        camera_id=camera_id,
                        source_id=source_id,
                        stream_url=stream_url,
                        session_id=session_id,
                        started_at=started_at,
                        ok=False,
                        state="read_failed",
                        error="Stream frame read failed or stream ended.",
                        last_frame_at=None,
                        inserted_rows=inserted_rows,
                    )
                    break

            elapsed_since_process = loop_started_at - last_processed_at
            if elapsed_since_process < STREAM_PROCESS_INTERVAL_SECONDS:
                stop_event.wait(STREAM_PROCESS_INTERVAL_SECONDS - elapsed_since_process)
                continue

            last_processed_at = time.monotonic()
            frame_count += 1
            frame = resize_for_detection(frame, STREAM_MAX_FRAME_WIDTH)
            # Outlier handling: CLAHE for low-light / poor-contrast frames
            # before YOLO runs. Tracker still receives the unmodified `frame`
            # (which is used both for ReID embeddings and the dashboard JPEG),
            # so the visual output stays natural.
            if STREAM_CLAHE_ENABLED:
                detection_frame = apply_clahe(frame)
            else:
                detection_frame = frame
            frame_h = detection_frame.shape[0]
            detections = []
            results = model(detection_frame, verbose=False, imgsz=STREAM_YOLO_IMGSZ, conf=STREAM_YOLO_CONF)
            for result in results:
                for box in result.boxes:
                    if int(box.cls[0]) == 0:
                        confidence = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        bbox_xywh = [x1, y1, x2 - x1, y2 - y1]
                        # Drop too-small / too-large boxes (likely false positives).
                        if not is_bbox_size_valid(bbox_xywh, frame_h):
                            continue
                        detections.append((bbox_xywh, confidence, "person"))

            tracks = tracker.update_tracks(detections, frame=frame)
            now_mono = time.monotonic()
            current_present_ids = set()
            for track in tracks:
                if not track.is_confirmed():
                    continue
                # Recently-seen tolerance: a brief miss (occlusion) still counts
                # as "present" so we don't fire OUT immediately and then IN again
                # when the same person re-enters detection.
                if not is_track_recently_seen(track):
                    continue

                track_id = track.track_id
                l, t, r, b = map(int, track.to_ltrb())
                current_present_ids.add(track_id)
                last_bbox_by_track[track_id] = (l, t, r, b)

                # Update displacement bookkeeping. A real person crossing the
                # frame accumulates pixels of movement; a stationary false
                # positive does not.
                cx = (l + r) // 2
                cy = (t + b) // 2
                first = track_first_center.get(track_id)
                if first is None:
                    track_first_center[track_id] = (cx, cy)
                    track_max_displacement[track_id] = 0
                else:
                    dx = cx - first[0]
                    dy = cy - first[1]
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist > track_max_displacement.get(track_id, 0):
                        track_max_displacement[track_id] = dist

                if is_track_visible(track):
                    cv2.rectangle(frame, (l, t), (r, b), (255, 0, 0), 2)
                    cv2.putText(frame, f"ID:{track_id}", (l, t - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            if STREAM_LINE_CROSSING_ENABLED:
                # ---- Line-crossing counter (production-grade) ----
                # Each track fires at most one IN and one OUT over its lifetime,
                # only when its bbox centre actually crosses the configured line.
                # This eliminates the over-counting that presence-based logic
                # produces when YOLO loses + re-acquires the same person.
                fh, fw = frame.shape[:2]
                line_pixel = compute_line_pixel(fw, fh, STREAM_LINE_ORIENTATION, STREAM_LINE_POSITION)

                for tid in current_present_ids:
                    l, t, r, b = last_bbox_by_track.get(tid, (0, 0, 1, 1))
                    center = ((l + r) // 2, (t + b) // 2)
                    curr_side = determine_side(center, STREAM_LINE_ORIENTATION, line_pixel)
                    prev_side = track_side.get(tid)
                    if prev_side is None:
                        track_side[tid] = curr_side
                        continue

                    direction = crossing_direction(
                        prev_side, curr_side,
                        STREAM_LINE_ORIENTATION, STREAM_LINE_IN_SIDE,
                    )
                    if direction is not None:
                        # Require displacement before honouring a crossing — guards
                        # against jitter teleporting a bbox across the line.
                        if track_max_displacement.get(tid, 0) >= STREAM_MIN_TRACK_DISPLACEMENT_PX:
                            already = track_crossed_directions.setdefault(tid, set())
                            if direction not in already:
                                already.add(direction)
                                bbox = (l, t, r, b)
                                db.insert_detection(
                                    track_id=tid,
                                    obj_class="person",
                                    confidence=1.0,
                                    bbox=bbox,
                                    frame_number=frame_count,
                                    direction=direction,
                                    session_id=session_id,
                                    table="live_logs",
                                )
                                inserted_rows += 1
                                if direction == "IN":
                                    active_track_ids.add(tid)
                                else:  # OUT
                                    active_track_ids.discard(tid)
                    track_side[tid] = curr_side

                # Garbage-collect state for tracks that have left the frame.
                for tid in list(track_side.keys()):
                    if tid not in current_present_ids:
                        track_side.pop(tid, None)
                        track_crossed_directions.pop(tid, None)
                        last_bbox_by_track.pop(tid, None)
                        track_first_center.pop(tid, None)
                        track_max_displacement.pop(tid, None)
                        active_track_ids.discard(tid)

                # Draw the counting line on the annotated frame (cyan, 2 px) so
                # the dashboard preview + recorded clip show exactly where the
                # threshold is. Saves manual diagnosis.
                if STREAM_LINE_ORIENTATION == "vertical":
                    cv2.line(frame, (line_pixel, 0), (line_pixel, fh), (0, 255, 255), 2)
                    label_in = "IN →" if STREAM_LINE_IN_SIDE in ("right", "east") else "← IN"
                else:
                    cv2.line(frame, (0, line_pixel), (fw, line_pixel), (0, 255, 255), 2)
                    label_in = "IN ↓" if STREAM_LINE_IN_SIDE in ("down", "below", "bottom") else "IN ↑"
                cv2.putText(frame, label_in, (10, max(20, line_pixel - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                current_occupancy = len(active_track_ids)
            else:
                # ---- Legacy presence-based counting (fallback) ----
                # Kept so the original behaviour is recoverable via the config flag.
                # Same logic as before Phase 9.
                newly_in = set()
                for tid in current_present_ids:
                    if tid in active_track_ids:
                        continue
                    first_seen = pending_in_since.get(tid)
                    if first_seen is None:
                        pending_in_since[tid] = now_mono
                        continue
                    if (now_mono - first_seen) < STREAM_IN_DEBOUNCE_SECONDS:
                        continue
                    if (STREAM_MIN_TRACK_DISPLACEMENT_PX > 0
                            and track_max_displacement.get(tid, 0) < STREAM_MIN_TRACK_DISPLACEMENT_PX):
                        continue
                    newly_in.add(tid)

                for tid in list(pending_in_since.keys()):
                    if tid not in current_present_ids:
                        pending_in_since.pop(tid, None)
                        track_first_center.pop(tid, None)
                        track_max_displacement.pop(tid, None)

                for track_id in newly_in:
                    bbox = last_bbox_by_track.get(track_id, (0, 0, 1, 1))
                    db.insert_detection(
                        track_id=track_id, obj_class="person", confidence=1.0,
                        bbox=bbox, frame_number=frame_count, direction="IN",
                        session_id=session_id, table="live_logs",
                    )
                    inserted_rows += 1
                    pending_in_since.pop(track_id, None)
                    active_track_ids.add(track_id)

                outgoing = active_track_ids - current_present_ids
                for track_id in outgoing:
                    bbox = last_bbox_by_track.get(track_id, (0, 0, 1, 1))
                    db.insert_detection(
                        track_id=track_id, obj_class="person", confidence=1.0,
                        bbox=bbox, frame_number=frame_count, direction="OUT",
                        session_id=session_id, table="live_logs",
                    )
                    inserted_rows += 1
                    last_bbox_by_track.pop(track_id, None)
                    track_first_center.pop(track_id, None)
                    track_max_displacement.pop(track_id, None)
                    active_track_ids.discard(track_id)

                current_occupancy = len(active_track_ids)

            last_frame_at = datetime.now().astimezone().isoformat()
            now_monotonic = time.monotonic()
            if now_monotonic - last_jpeg_at >= STREAM_JPEG_INTERVAL_SECONDS:
                cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 55])
                last_jpeg_at = now_monotonic

            # DVR recording: persist the annotated frame to a rolling MP4 chunk
            # so the dashboard timeline slider can play back any past minute.
            if recorder is not None:
                recorder.write(frame)

            _status(
                status_queue,
                camera_id=camera_id,
                source_id=source_id,
                stream_url=stream_url,
                session_id=session_id,
                started_at=started_at,
                ok=True,
                state="running",
                error=None,
                last_frame_at=last_frame_at,
                inserted_rows=inserted_rows,
                frame_count=frame_count,
                current_occupancy=current_occupancy,
            )

            elapsed = time.monotonic() - loop_started_at
            if elapsed < STREAM_PROCESS_INTERVAL_SECONDS:
                stop_event.wait(STREAM_PROCESS_INTERVAL_SECONDS - elapsed)

    except Exception as exc:
        _status(
            status_queue,
            camera_id=camera_id,
            source_id=source_id,
            stream_url=stream_url,
            session_id=session_id,
            started_at=started_at,
            ok=False,
            state="error",
            error=str(exc),
            last_frame_at=None,
            inserted_rows=inserted_rows,
            frame_count=frame_count,
            current_occupancy=current_occupancy,
        )
    finally:
        if cap is not None:
            cap.release()
        if db is not None:
            db.close()
        if recorder is not None:
            try:
                recorder.close()
            except Exception:
                pass

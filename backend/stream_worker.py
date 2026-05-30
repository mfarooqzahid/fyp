import os
import time
from datetime import datetime

try:
    from backend.config import DEEPSORT_MAX_AGE, MODEL_PATH
except Exception:
    from config import DEEPSORT_MAX_AGE, MODEL_PATH


BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR = os.path.join(BACKEND_DIR, "frames")


def is_track_visible(track):
    """Return True only when DeepSORT updated this track from the current frame."""
    return getattr(track, "time_since_update", 0) == 0


def get_presence_events(previous_active_ids, current_active_ids):
    return {
        "incoming": set(current_active_ids) - set(previous_active_ids),
        "outgoing": set(previous_active_ids) - set(current_active_ids),
    }


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
        try:
            from backend.db_handler import DBHandler
        except Exception:
            from db_handler import DBHandler
        from deep_sort_realtime.deepsort_tracker import DeepSort
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
    active_track_ids = set()
    last_bbox_by_track = {}
    frame_count = 0
    inserted_rows = 0
    current_occupancy = 0

    model = tracker = db = cap = None
    try:
        model = YOLO(MODEL_PATH)
        tracker = DeepSort(max_age=DEEPSORT_MAX_AGE)
        db = DBHandler(camera_id=camera_id)
        
        is_youtube = "youtube.com" in stream_url.lower() or "youtu.be" in stream_url.lower()
        if is_youtube:
            try:
                import yt_dlp
                ydl_opts = {
                    'format': 'best[ext=mp4]/best',
                    'quiet': True,
                    'no_warnings': True
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
            ret, frame = cap.read()
            if not ret:
                print(f"[STREAM LOOP] Stream ended or frame read failed. Rewinding connection for continuous playback...")
                # 1. Try to seek to frame 0 first (fastest for files)
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                
                # 2. If seeking fails (typical for network/YouTube streams), re-initialize the VideoCapture
                if not ret:
                    cap.release()
                    if is_youtube:
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

            frame_count += 1
            detections = []
            results = model(frame, verbose=False)
            for result in results:
                for box in result.boxes:
                    if int(box.cls[0]) == 0:
                        confidence = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        detections.append(([x1, y1, x2 - x1, y2 - y1], confidence, "person"))

            tracks = tracker.update_tracks(detections, frame=frame)
            current_track_ids = set()
            for track in tracks:
                if not track.is_confirmed():
                    continue
                if not is_track_visible(track):
                    continue

                track_id = track.track_id
                l, t, r, b = map(int, track.to_ltrb())
                current_track_ids.add(track_id)
                last_bbox_by_track[track_id] = (l, t, r, b)

                cv2.rectangle(frame, (l, t), (r, b), (255, 0, 0), 2)
                cv2.putText(frame, f"ID:{track_id}", (l, t - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            events = get_presence_events(active_track_ids, current_track_ids)

            for track_id in events["incoming"]:
                bbox = last_bbox_by_track.get(track_id, (0, 0, 1, 1))
                db.insert_detection(
                    track_id=track_id,
                    obj_class="person",
                    confidence=1.0,
                    bbox=bbox,
                    frame_number=frame_count,
                    direction="IN",
                    session_id=session_id,
                    table="live_logs",
                )
                inserted_rows += 1

            for track_id in events["outgoing"]:
                bbox = last_bbox_by_track.get(track_id, (0, 0, 1, 1))
                db.insert_detection(
                    track_id=track_id,
                    obj_class="person",
                    confidence=1.0,
                    bbox=bbox,
                    frame_number=frame_count,
                    direction="OUT",
                    session_id=session_id,
                    table="live_logs",
                )
                inserted_rows += 1
                last_bbox_by_track.pop(track_id, None)

            active_track_ids = current_track_ids
            current_occupancy = len(active_track_ids)

            last_frame_at = datetime.now().astimezone().isoformat()
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 60])

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

            time.sleep(0.001)

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

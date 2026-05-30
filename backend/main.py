import cv2
import os
import sys
import json
from datetime import datetime
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from db_handler import DBHandler
from config import MODEL_PATH, DEFAULT_VIDEO_PATH, DEEPSORT_MAX_AGE

# Core Components
model = YOLO(MODEL_PATH)
tracker = DeepSort(max_age=DEEPSORT_MAX_AGE)

# Global State
active_track_ids = set()
last_bbox_by_track = {}
frame_count = 0
current_occupancy = 0

# Hardware/Source Discovery
video_source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VIDEO_PATH
cap = cv2.VideoCapture(video_source)

if not cap.isOpened():
    print(f"Critical Error: Source {video_source} unavailable.")
    sys.exit(1)

print(f"Analysis Started: {video_source}")

# Generate a unique Session ID for this run to keep data isolated
ACTIVE_SESSION_ID = f"{os.path.basename(video_source)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
ACTIVE_CAMERA_ID = os.path.splitext(os.path.basename(video_source))[0] or "audit_camera"
db = DBHandler(camera_id=ACTIVE_CAMERA_ID)

# Signals
STOP_SIGNAL = os.path.join(os.path.dirname(__file__), "stop_signal.txt")
if os.path.exists(STOP_SIGNAL): os.remove(STOP_SIGNAL)

while True:
    if os.path.exists(STOP_SIGNAL):
        print("Interrupt signal received. Cleaning up...")
        break

    ret, frame = cap.read()
    if not ret:
        print("[LOOP] Video file ended. Rewinding for continuous playback...")
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = cap.read()
        if not ret:
            print("Source stream consumed.")
            break

    frame_count += 1
    # YOLO Inference
    results = model(frame, verbose=False)
    detections = []
    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) == 0: # person
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append(([x1, y1, x2-x1, y2-y1], conf, 'person'))

    # Tracking Updates
    tracks = tracker.update_tracks(detections, frame=frame)
    current_track_ids = set()
    for track in tracks:
        if not track.is_confirmed(): continue
        if getattr(track, "time_since_update", 0) != 0: continue
        
        tid = track.track_id
        l, t, r, b = map(int, track.to_ltrb())
        current_track_ids.add(tid)
        last_bbox_by_track[tid] = (l, t, r, b)

        cv2.rectangle(frame, (l, t), (r, b), (255, 0, 0), 2)
        cv2.putText(frame, f"ID:{tid}", (l, t-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    session_label = ACTIVE_SESSION_ID
    target_table = "audit_logs" if os.path.isfile(video_source) else "live_logs"
    incoming_ids = current_track_ids - active_track_ids
    outgoing_ids = active_track_ids - current_track_ids

    for tid in incoming_ids:
        db.insert_detection(tid, "person", 1.0, last_bbox_by_track.get(tid, (0, 0, 1, 1)), frame_count, "IN",
                            session_id=session_label, table=target_table)
        print(f"Frame Entry Detected [{target_table}]: ID {tid} -> IN")

    for tid in outgoing_ids:
        db.insert_detection(tid, "person", 1.0, last_bbox_by_track.get(tid, (0, 0, 1, 1)), frame_count, "OUT",
                            session_id=session_label, table=target_table)
        last_bbox_by_track.pop(tid, None)
        print(f"Frame Exit Detected [{target_table}]: ID {tid} -> OUT")

    active_track_ids = current_track_ids
    current_occupancy = len(active_track_ids)

    # Frame Export for Dashboard
    try:
        current_frame_path = os.path.join(os.path.dirname(__file__), "current_frame.jpg")
        cv2.imwrite(current_frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
    except: pass

# Post-Session Summary
print("--- Finalizing Audit Session ---")
cap.release()

session_ref = ACTIVE_SESSION_ID
target_table = "audit_logs" if os.path.isfile(video_source) else "live_logs"
final_in = db.get_total_visitors(session_id=session_ref, direction='IN', table=target_table)
final_out = db.get_total_visitors(session_id=session_ref, direction='OUT', table=target_table)

audit_summary = {
    "session": session_ref,
    "total_in": final_in,
    "total_out": final_out,
    "current_occupancy": current_occupancy,
    "total_flow": final_in + final_out,
    "status": "SUCCESS",
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

sum_path = os.path.join(os.path.dirname(__file__), "audit_summary.json")
comp_path = os.path.join(os.path.dirname(__file__), "audit_complete.txt")

with open(sum_path, "w") as f: json.dump(audit_summary, f)
with open(comp_path, "w") as f: f.write("DONE")

db.close()
cv2.destroyAllWindows()
print("Audit processing completed successfully.")

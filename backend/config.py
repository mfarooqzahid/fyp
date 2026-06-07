MODEL_PATH         = "yolov8n.pt"
DEFAULT_VIDEO_PATH = "videos/sample.mp4"

# DeepSort: keep tracks alive across brief occlusions (frames of no detection).
# Raised from 60 → 120 so a track survives ~60 seconds at 2 fps without losing
# its ID. Lower values caused the same person to be re-counted as a new track
# whenever YOLO momentarily missed them (motion blur, partial occlusion).
DEEPSORT_MAX_AGE   = 120

# YOLO detection confidence for live streams. Raised from 0.25 → 0.35 → 0.5
# to suppress flickering low-confidence boxes that create phantom tracks. On
# phone-camera / low-resolution sources this is the single biggest win.
STREAM_YOLO_CONF   = 0.5

# Suppress duplicate IN events: a brand-new track must be continuously visible
# for at least this many seconds before its IN row is written to live_logs.
# 3.0 sec means a person briefly walking past won't trigger an IN unless they
# linger — eliminates the most common cause of inflated counts.
STREAM_IN_DEBOUNCE_SECONDS = 3.0

# Tolerate brief detection misses: a track that drops out for up to this many
# processed frames is still treated as "present", so we don't fire a false OUT
# (and then a false IN when it reappears). Raised from 10 → 40 (~20 sec at
# 2 fps) so partial occlusions don't reset the track.
STREAM_TRACK_MISS_TOLERANCE_FRAMES = 40

# Minimum pixel displacement a track must accumulate over its lifetime before
# we count it as a real "person passing through" rather than a stationary
# false positive (chair, shadow, poster, etc.). Disable with 0.
STREAM_MIN_TRACK_DISPLACEMENT_PX = 40

# CLAHE (Contrast Limited Adaptive Histogram Equalization): boosts local
# contrast on the luminance channel so YOLO can detect people in low-light or
# under-exposed frames. Disable if your footage is already well-lit and you
# want to save the ~2-3 ms per frame.
STREAM_CLAHE_ENABLED   = True
STREAM_CLAHE_CLIP_LIMIT = 2.0
STREAM_CLAHE_TILE_GRID  = 8

# Bbox sanity filter: drop detections whose height is too small (likely noise
# / partial detections from far away) or too large relative to the frame
# (likely a false positive on a wall, door, or full-frame object).
STREAM_MIN_BBOX_HEIGHT_PX     = 30
STREAM_MAX_BBOX_HEIGHT_RATIO  = 0.95

# DVR-style recording: each camera's annotated stream is sliced into N-second
# MP4 chunks under backend/recordings/{camera_id}/{YYYYMMDD}/{HHMMSS}.mp4.
# Older chunks are pruned beyond the retention window. The dashboard timeline
# slider serves these files via /api/playback/{camera_id}/clip.
STREAM_RECORDING_ENABLED          = True
STREAM_RECORDING_CHUNK_SECONDS    = 60
STREAM_RECORDING_RETENTION_HOURS  = 6

# --- Line-crossing counter (production-grade counting) ---
# Instead of counting "track appeared in frame" (presence-based — which over-
# counts when the same person briefly gets a new track ID), count only when a
# track's bbox centre crosses an imaginary line drawn through the frame.
# Each track fires each direction at most once, eliminating the duplicate
# IN/OUT events caused by YOLO detection gaps + DeepSort track resets.
#
# Disable with STREAM_LINE_CROSSING_ENABLED=False to fall back to the legacy
# presence-based logic.
STREAM_LINE_CROSSING_ENABLED   = True

# Orientation: "horizontal" (line spans left-right at given y),
#              "vertical"   (line spans top-bottom at given x)
STREAM_LINE_ORIENTATION        = "horizontal"

# Position as a fraction of the relevant dimension. 0.5 = centre of frame.
# For an overhead view of a corridor, 0.5 is usually best.
STREAM_LINE_POSITION           = 0.5

# Which side of the line is "IN". For horizontal: "down" means below the
# line is the IN zone (track crossing top→bottom is logged IN). For
# vertical: "right" means right of the line is IN.
STREAM_LINE_IN_SIDE            = "down"

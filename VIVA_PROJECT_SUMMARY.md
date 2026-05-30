# Capmus Mobility & Occupancy Analytics System

## Brief Project Summary

Capmus is a smart camera based mobility and occupancy analytics system. It monitors people visible in camera feeds, records when people appear in the frame as incoming movement, records when they disappear from the frame as outgoing movement, and uses the current visible people count as occupancy. The system provides a dashboard for real-time and historical analytics such as occupancy, incoming/outgoing flow, rush detection, congestion, trends, and camera comparison.

## What The Project Does

- Manages multiple camera sources.
- Supports generated/simulated camera data and real stream sources.
- Detects people in video frames.
- Tracks visible people across frames.
- Counts a new tracked person appearing in the frame as `IN`.
- Counts a previously visible tracked person leaving the frame as `OUT`.
- Treats the current number of visible tracked people as occupancy.
- Stores movement events in Supabase/PostgreSQL.
- Displays analytics through a React dashboard.

## Why The Project Was Built

The project was built to help monitor crowd movement and occupancy in areas such as university gates, corridors, building entrances, public spaces, and event venues. It helps administrators understand how many people are currently present, how many are entering or leaving, when rush periods occur, and which camera locations are busiest.

## Who Uses It

The intended users are campus administrators, security teams, facility managers, or operations staff. They can use the dashboard to monitor crowd density, identify high-traffic areas, and respond to rush or congestion.

## Where It Can Be Used

- University campuses
- Office buildings
- Shopping malls
- Event venues
- Transport stations
- Entry/exit monitoring points
- Corridors or public areas covered by cameras

## When It Works

The system works in near real time. Background workers continuously generate or process camera data. The frontend periodically refreshes analytics from the backend, so users can see updated occupancy, flow, and rush status without manually querying the database.

## How It Works

The project has three main layers:

1. Frontend
   - Built with React and Vite.
   - Shows camera sources, metrics, charts, and analytics.
   - Uses ECharts for visualizations.
   - Calls FastAPI endpoints through `/api`.

2. Backend
   - Built with FastAPI.
   - Provides APIs for source management, dashboard analytics, frame access, simulator workers, and stream workers.
   - Uses an analytics engine to combine calculations into one dashboard response.
   - Uses worker supervisors to start, stop, restart, and monitor background data workers.

3. Database
   - Uses Supabase/PostgreSQL.
   - Stores camera source definitions and movement logs.
   - Main tables are `camera_sources`, `simulated_logs`, `live_logs`, and `audit_logs`.

## Technical Stack

- Backend: Python, FastAPI, Pydantic, Uvicorn
- Frontend: React, Vite, JavaScript
- Charts: ECharts and echarts-for-react
- Database: Supabase/PostgreSQL
- Computer vision: OpenCV, YOLO from Ultralytics, DeepSORT
- Testing: Python unittest/pytest-compatible tests

## Important Backend Components

- `backend/api.py`: Main FastAPI app and API routes.
- `backend/stream_worker.py`: Processes live streams, detects people, tracks frame presence, and writes `IN`/`OUT` events.
- `backend/main.py`: Processes video/audit sources with the same frame-presence counting approach.
- `backend/analytics_engine.py`: Central coordinator for dashboard data.
- `backend/analytics_service.py`: Queries Supabase and calculates analytics.
- `backend/rush_detection.py`: Detects abnormal traffic using recent counts, historical average, standard deviation, z-score, and ratio.
- `backend/source_repository.py`: Handles camera source CRUD operations.
- `backend/db_handler.py`: Inserts detection events into Supabase.
- `backend/simulator_supervisor.py`: Manages generated data workers.
- `backend/stream_supervisor.py`: Manages live stream workers.

## Important Frontend Components

- `frontend/src/App.jsx`: Main React app shell.
- `frontend/src/components/Sidebar.jsx`: Camera/source selection.
- `frontend/src/components/Dashboard.jsx`: Main dashboard metrics and charts.
- `frontend/src/components/AddSourceModal.jsx`: Adds new camera sources.
- `frontend/src/services/sourcesApi.js`: API calls to the backend.

## Data Modes

- `generate`, `simulation`, or `simulated`: generated data stored in `simulated_logs`.
- `stream` or `live`: real stream data stored in `live_logs`.
- `audit`: recorded video/session data stored in `audit_logs`.

## Computer Vision Logic

For real streams, the system reads frames using OpenCV. YOLO detects people in each frame. DeepSORT assigns a stable tracking ID to each detected person. The system keeps a set of currently visible track IDs:

- If a track ID is visible now but was not visible in the previous frame, it is counted as `IN`.
- If a track ID was visible before but is no longer visible now, it is counted as `OUT`.
- The number of currently visible track IDs is the live camera occupancy.

This simplified model does not rely on manually placing or crossing a virtual line.

## Analytics Logic

The backend stores each `IN` and `OUT` event with camera ID, timestamp, session ID, object class, confidence, bounding box, and frame number. The analytics service queries these events and calculates:

- Current occupancy
- Incoming count
- Outgoing count
- Flow split
- Peak time slots
- Hourly trend
- Daily trend
- Live occupancy trend
- Gate/camera comparison
- Congestion level
- Week-over-week change
- Rush status

For dashboard analytics, occupancy is represented from the event log as `IN - OUT`. Because the stream worker now logs `IN` when a person appears and `OUT` when a person disappears, this value represents the number of people currently visible in the camera for the active session.

## Rush Detection

Rush detection compares recent traffic volume with historical behavior for the same time period. It uses:

- Current movement count in a recent time window
- Historical mean
- Standard deviation
- Z-score
- Ratio of current traffic to average traffic

The system labels the status as normal, busy, or rush alert depending on how abnormal the current movement is.

## Main API Endpoints

- `GET /api/health`
- `GET /api/sources`
- `POST /api/sources`
- `PUT /api/sources/{source_id}`
- `DELETE /api/sources/{source_id}`
- `GET /api/dashboard`
- `GET /api/camera_comparison`
- `GET /api/frame`
- `GET /api/simulator/workers`
- `GET /api/stream/workers`

## Strengths

- Supports both generated data and live camera streams.
- Uses real computer vision models for detection and tracking.
- Avoids manual line placement by using frame presence.
- Separates frontend, backend, database, analytics, and worker responsibilities.
- Provides practical metrics instead of only raw detection output.
- Includes worker supervision for background simulator and stream processing.
- Includes tests for analytics, rush detection, stream presence logic, source loading, and frame retrieval.

## Limitations

- Accuracy depends on camera angle, lighting, occlusion, and stream quality.
- If the detector briefly misses a person, the system may treat that as an outgoing event and then a new incoming event when the person is detected again.
- The system depends on YOLO and DeepSORT performance.
- Supabase credentials and database migrations are required before full operation.
- GPU acceleration may be needed for smoother real-time stream processing.
- Average wait time is unavailable because the current schema does not maintain complete first-seen and last-seen timing per person.

## One-Minute Viva Explanation

It is a smart camera mobility and occupancy analytics system. It uses camera streams or simulated sources to monitor how many people are visible in an area. YOLO detects people in video frames, and DeepSORT tracks them across frames. When a new tracked person appears in the frame, the system counts it as incoming. When a previously visible person disappears, it counts it as outgoing. The current number of visible tracked people is treated as occupancy. These events are stored in Supabase/PostgreSQL and analyzed by a FastAPI backend. The React dashboard displays real-time occupancy, incoming and outgoing flow, peak times, rush alerts, congestion levels, trends, and camera comparisons.

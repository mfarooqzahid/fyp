"""
====================================================================
FYP FULL SYSTEM UNIT TEST SUITE
====================================================================
Covers:
  - stream_worker  : crossing direction logic
  - stream_supervisor : source loading / stream filtering
  - api            : /api/frame endpoint (camera + fallback + 404)
  - analytics_service : occupancy, flow split, peak slots,
                        gate comparison, congestion levels,
                        week-over-week, daily summary,
                        running occupancy points, count helpers
  - rush_detection : z-score pipeline, alert thresholds (NORMAL/BUSY/RUSH)
  - config         : required constants present
====================================================================
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Make sure the project root is importable regardless of how pytest is invoked
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.dirname(os.path.abspath(__file__))
for p in [ROOT, os.path.dirname(BACKEND)]:
    if p not in sys.path:
        sys.path.insert(0, p)


# ===========================================================================
# 1. CONFIG TESTS
# ===========================================================================
class ConfigTest(unittest.TestCase):
    """Verify that config exports required constants and they have sensible types."""

    def test_model_path_is_string(self):
        from backend.config import MODEL_PATH
        self.assertIsInstance(MODEL_PATH, str)
        self.assertTrue(len(MODEL_PATH) > 0, "MODEL_PATH must not be empty")

    def test_deepsort_max_age_is_positive_int(self):
        from backend.config import DEEPSORT_MAX_AGE
        self.assertIsInstance(DEEPSORT_MAX_AGE, int)
        self.assertGreater(DEEPSORT_MAX_AGE, 0)

    def test_line_orientation_is_valid(self):
        from backend.config import LINE_ORIENTATION
        self.assertIn(LINE_ORIENTATION, ("horizontal", "vertical"))

    def test_default_camera_id_is_string(self):
        from backend.config import DEFAULT_CAMERA_ID
        self.assertIsInstance(DEFAULT_CAMERA_ID, str)
        self.assertTrue(len(DEFAULT_CAMERA_ID) > 0)


# ===========================================================================
# 2. STREAM WORKER – crossing direction logic
# ===========================================================================
class StreamDirectionTest(unittest.TestCase):
    """Unit-test the pure crossing-direction function (no CV / YOLO needed)."""

    def setUp(self):
        from backend.stream_worker import get_crossing_direction
        self.fn = get_crossing_direction

    # -- basic crossings --------------------------------------------------
    def test_left_to_right_is_IN(self):
        self.assertEqual(self.fn(90, 110, 100), "IN")

    def test_right_to_left_is_OUT(self):
        self.assertEqual(self.fn(110, 90, 100), "OUT")

    def test_no_crossing_returns_None(self):
        self.assertIsNone(self.fn(80, 95, 100))

    # -- edge cases: exactly on the line ----------------------------------
    def test_moving_onto_line_exactly_is_IN(self):
        # previous=99, current=100, line=100 → crosses onto line → IN
        self.assertEqual(self.fn(99, 100, 100), "IN")

    def test_moving_off_line_is_OUT(self):
        # previous=101, current=100, line=100 → crosses line from right → OUT
        self.assertEqual(self.fn(101, 100, 100), "OUT")

    def test_stationary_on_line_is_None(self):
        self.assertIsNone(self.fn(100, 100, 100))

    def test_stationary_before_line_is_None(self):
        self.assertIsNone(self.fn(50, 50, 100))

    def test_stationary_after_line_is_None(self):
        self.assertIsNone(self.fn(150, 150, 100))


# ===========================================================================
# 3. STREAM SUPERVISOR – source loading
# ===========================================================================
class StreamSupervisorSourceTest(unittest.TestCase):
    """Verify that the supervisor correctly filters stream vs generate sources."""

    def _make_supervisor(self):
        from backend import stream_supervisor
        return stream_supervisor.StreamSupervisor()

    def test_loads_only_stream_sources_from_repository(self):
        from backend import stream_supervisor

        class FakeRepository:
            def list_sources(self):
                return [
                    {"id": "s1", "mode": "stream",    "camera_id": "Cam_A", "streamUrl": "rtsp://a.test/live"},
                    {"id": "s2", "mode": "generate",  "camera_id": "Cam_B", "streamUrl": ""},
                    {"id": "s3", "source_type": "stream", "camera_id": "Cam_C", "streamUrl": "http://c.test/live"},
                ]

        sup = self._make_supervisor()
        with patch.object(stream_supervisor, "SourceRepository", FakeRepository):
            sources = sup._load_stream_sources()

        self.assertIn("Cam_A", sources)
        self.assertIn("Cam_C", sources)
        self.assertNotIn("Cam_B", sources)

    def test_stream_url_stored_correctly(self):
        from backend import stream_supervisor

        class FakeRepository:
            def list_sources(self):
                return [{"id": "s1", "mode": "stream", "camera_id": "Cam_X", "streamUrl": "rtsp://x.test/live"}]

        sup = self._make_supervisor()
        with patch.object(stream_supervisor, "SourceRepository", FakeRepository):
            sources = sup._load_stream_sources()

        self.assertEqual(sources["Cam_X"]["stream_url"], "rtsp://x.test/live")

    def test_generates_only_source_is_excluded(self):
        from backend import stream_supervisor

        class FakeRepository:
            def list_sources(self):
                return [{"id": "g1", "mode": "generate", "camera_id": "Cam_G", "streamUrl": ""}]

        sup = self._make_supervisor()
        with patch.object(stream_supervisor, "SourceRepository", FakeRepository):
            sources = sup._load_stream_sources()

        self.assertEqual(sources, {})

    def test_source_with_missing_stream_url_excluded(self):
        from backend import stream_supervisor

        class FakeRepository:
            def list_sources(self):
                return [{"id": "s9", "mode": "stream", "camera_id": "Cam_Z", "streamUrl": None}]

        sup = self._make_supervisor()
        with patch.object(stream_supervisor, "SourceRepository", FakeRepository):
            sources = sup._load_stream_sources()

        self.assertNotIn("Cam_Z", sources)


# ===========================================================================
# 4. API – /api/frame endpoint
# ===========================================================================
class ApiFrameTest(unittest.TestCase):
    """Test the FastAPI frame-serving endpoint without starting a live server."""

    def test_per_camera_frame_is_served(self):
        from backend import api
        with tempfile.TemporaryDirectory() as tmp:
            frames_dir = os.path.join(tmp, "frames")
            os.makedirs(frames_dir)
            frame_path = os.path.join(frames_dir, "Camera_abc.jpg")
            with open(frame_path, "wb") as f:
                f.write(b"fake-jpeg")
            with patch.object(api, "BACKEND_DIR", tmp):
                response = api.frame(camera="Camera_abc")
        self.assertEqual(response.path, frame_path)

    def test_missing_camera_frame_raises_404(self):
        from backend import api
        from fastapi import HTTPException
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(api, "BACKEND_DIR", tmp):
                with self.assertRaises(HTTPException) as ctx:
                    api.frame(camera="Camera_missing")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_fallback_to_current_frame_jpg(self):
        from backend import api
        with tempfile.TemporaryDirectory() as tmp:
            fallback = os.path.join(tmp, "current_frame.jpg")
            with open(fallback, "wb") as f:
                f.write(b"fake-jpeg")
            with patch.object(api, "BACKEND_DIR", tmp):
                response = api.frame(camera=None)
        self.assertEqual(response.path, fallback)

    def test_path_traversal_is_rejected(self):
        """Ensure camera=../secret does not escape the frames directory."""
        from backend import api
        from fastapi import HTTPException
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(api, "BACKEND_DIR", tmp):
                with self.assertRaises(HTTPException):
                    api.frame(camera="../secret")


# ===========================================================================
# 5. ANALYTICS SERVICE – helper to build fake service
# ===========================================================================
def _fake_analytics_service(rows):
    """
    Returns an AnalyticsService instance whose _query_logs method
    is monkey-patched to return `rows` (applying standard filters).
    No Supabase connection is made.
    """
    from backend.analytics_service import AnalyticsService
    svc = AnalyticsService.__new__(AnalyticsService)

    def query_logs(table="detections", camera_id=None, camera_ids=None,
                   session_id=None, direction=None, date=None,
                   start_dt=None, end_dt=None):
        result = list(rows)
        if camera_id:
            result = [r for r in result if r["camera_id"] == camera_id]
        if camera_ids is not None:
            result = [r for r in result if r["camera_id"] in camera_ids]
        if session_id:
            result = [r for r in result if r.get("session_id") == session_id]
        if direction:
            result = [r for r in result if r["direction"] == direction]
        if date:
            result = [r for r in result if r["timestamp"].startswith(date)]
        if start_dt:
            result = [r for r in result
                      if datetime.fromisoformat(r["timestamp"]) >= start_dt]
        if end_dt:
            result = [r for r in result
                      if datetime.fromisoformat(r["timestamp"]) <= end_dt]
        return result

    svc._query_logs = query_logs
    return svc


def _row(camera, direction, ts, session="S1"):
    return {"camera_id": camera, "direction": direction,
            "timestamp": ts.isoformat(), "session_id": session}


class AnalyticsOccupancyTest(unittest.TestCase):
    """get_realtime_occupancy – IN minus OUT, clamped to 0."""

    def _svc(self, rows):
        return _fake_analytics_service(rows)

    def test_normal_occupancy(self):
        now = datetime.now().astimezone()
        rows = [
            _row("Gate A", "IN",  now),
            _row("Gate A", "IN",  now),
            _row("Gate A", "OUT", now),
        ]
        result = self._svc(rows).get_realtime_occupancy(camera_id="Gate A")
        self.assertEqual(result["current"], 1)
        self.assertEqual(result["incoming"], 2)
        self.assertEqual(result["outgoing"], 1)

    def test_occupancy_never_goes_negative(self):
        now = datetime.now().astimezone()
        rows = [_row("Gate A", "OUT", now), _row("Gate A", "OUT", now)]
        result = self._svc(rows).get_realtime_occupancy(camera_id="Gate A")
        self.assertEqual(result["current"], 0)

    def test_empty_data_returns_zero(self):
        result = self._svc([]).get_realtime_occupancy(camera_id="Gate A")
        self.assertEqual(result["current"], 0)


class AnalyticsFlowSplitTest(unittest.TestCase):
    """get_flow_split – percentage arithmetic."""

    def _svc(self, rows):
        return _fake_analytics_service(rows)

    def test_75_percent_incoming(self):
        now = datetime.now().astimezone()
        rows = [
            _row("Gate A", "IN",  now),
            _row("Gate A", "IN",  now),
            _row("Gate A", "IN",  now),
            _row("Gate A", "OUT", now),
        ]
        result = self._svc(rows).get_flow_split(camera_id="Gate A")
        self.assertEqual(result["incoming_percent"], 75)
        self.assertEqual(result["outgoing_percent"], 25)

    def test_all_incoming_100_percent(self):
        now = datetime.now().astimezone()
        rows = [_row("Gate A", "IN", now), _row("Gate A", "IN", now)]
        result = self._svc(rows).get_flow_split(camera_id="Gate A")
        self.assertEqual(result["incoming_percent"], 100)
        self.assertEqual(result["outgoing_percent"], 0)

    def test_empty_flow_returns_zero_percent(self):
        result = self._svc([]).get_flow_split(camera_id="Gate A")
        self.assertEqual(result["incoming_percent"], 0)
        self.assertEqual(result["outgoing_percent"], 0)
        self.assertEqual(result["total"], 0)


class AnalyticsPeakSlotsTest(unittest.TestCase):
    """get_peak_slots – bucket grouping and sorting."""

    def _svc(self, rows):
        return _fake_analytics_service(rows)

    def test_peak_slot_has_most_entries(self):
        now = datetime.now().astimezone().replace(hour=9, minute=0, second=0, microsecond=0)
        rows = [
            _row("Gate A", "IN", now.replace(hour=8, minute=5)),
            _row("Gate A", "IN", now.replace(hour=8, minute=10)),  # 2 in 8:00 slot
            _row("Gate A", "IN", now.replace(hour=9, minute=5)),   # 1 in 9:00 slot
        ]
        peaks = self._svc(rows).get_peak_slots(camera_id="Gate A", bucket_minutes=30, limit=2)
        self.assertEqual(peaks[0]["count"], 2)
        self.assertIn("8:", peaks[0]["time"])

    def test_empty_returns_empty_list(self):
        peaks = self._svc([]).get_peak_slots(camera_id="Gate A")
        self.assertEqual(peaks, [])


class AnalyticsGateComparisonTest(unittest.TestCase):
    """get_gate_comparison – multi-gate traffic share."""

    def _svc(self, rows):
        return _fake_analytics_service(rows)

    def test_gate_with_most_traffic_is_first(self):
        now = datetime.now().astimezone()
        rows = [
            _row("Gate A", "IN", now),
            _row("Gate A", "IN", now),
            _row("Gate A", "IN", now),  # Gate A: 3
            _row("Gate B", "IN", now),  # Gate B: 1
        ]
        gates = self._svc(rows).get_gate_comparison()
        self.assertEqual(gates[0]["camera"], "Gate A")
        self.assertEqual(gates[0]["traffic"], 3)
        self.assertEqual(gates[0]["percent"], 75)

    def test_single_gate_is_100_percent(self):
        now = datetime.now().astimezone()
        rows = [_row("Gate A", "IN", now), _row("Gate A", "IN", now)]
        gates = self._svc(rows).get_gate_comparison()
        self.assertEqual(gates[0]["percent"], 100)

    def test_empty_returns_empty_list(self):
        gates = self._svc([]).get_gate_comparison()
        self.assertEqual(gates, [])


class AnalyticsCongestionTest(unittest.TestCase):
    """get_congestion_levels – LOW / MEDIUM / HIGH classification."""

    def _svc(self, rows):
        return _fake_analytics_service(rows)

    def test_medium_congestion_at_50_percent(self):
        now = datetime.now().astimezone()
        rows = [
            _row("Gate A", "IN",  now),
            _row("Gate A", "IN",  now),  # max = 2
            _row("Gate A", "OUT", now),  # current = 1 (50 %)
        ]
        levels = self._svc(rows).get_congestion_levels(camera_id="Gate A")
        self.assertEqual(levels[0]["status"], "MEDIUM")
        self.assertEqual(levels[0]["percent"], 50)

    def test_high_congestion_at_100_percent(self):
        now = datetime.now().astimezone()
        rows = [
            _row("Gate A", "IN", now),
            _row("Gate A", "IN", now),   # max = current = 2
        ]
        levels = self._svc(rows).get_congestion_levels(camera_id="Gate A")
        self.assertEqual(levels[0]["status"], "HIGH")
        self.assertEqual(levels[0]["percent"], 100)

    def test_low_congestion_when_mostly_cleared(self):
        now = datetime.now().astimezone()
        rows = [
            _row("Gate A", "IN",  now),
            _row("Gate A", "IN",  now),
            _row("Gate A", "IN",  now),
            _row("Gate A", "OUT", now),
            _row("Gate A", "OUT", now),
            _row("Gate A", "OUT", now),  # current = 0, max = 3 → 0 % → LOW
        ]
        levels = self._svc(rows).get_congestion_levels(camera_id="Gate A")
        self.assertEqual(levels[0]["status"], "LOW")


class AnalyticsWeekOverWeekTest(unittest.TestCase):
    """get_week_over_week – direction and percentage change."""

    def _svc(self, rows):
        return _fake_analytics_service(rows)

    def test_traffic_increase_is_up(self):
        now = datetime.now().astimezone()
        this_week = now - timedelta(days=1)
        last_week = now - timedelta(days=8)
        rows = [
            _row("Gate A", "IN",  this_week),
            _row("Gate A", "OUT", this_week),   # this week total = 2
            _row("Gate A", "IN",  last_week),   # last week total = 1
        ]
        result = self._svc(rows).get_week_over_week(camera_id="Gate A")
        self.assertEqual(result["current_total"], 2)
        self.assertEqual(result["previous_total"], 1)
        self.assertEqual(result["change_percent"], 100)
        self.assertEqual(result["direction"], "up")

    def test_traffic_decrease_is_down(self):
        now = datetime.now().astimezone()
        this_week = now - timedelta(days=1)
        last_week = now - timedelta(days=8)
        rows = [
            _row("Gate A", "IN", this_week),               # this week = 1
            _row("Gate A", "IN", last_week),
            _row("Gate A", "IN", last_week),               # last week = 2
        ]
        result = self._svc(rows).get_week_over_week(camera_id="Gate A")
        self.assertEqual(result["direction"], "down")

    def test_no_previous_data_gives_100_percent_up(self):
        now = datetime.now().astimezone()
        rows = [_row("Gate A", "IN", now - timedelta(days=1))]
        result = self._svc(rows).get_week_over_week(camera_id="Gate A")
        self.assertEqual(result["previous_total"], 0)
        self.assertEqual(result["change_percent"], 100)
        self.assertEqual(result["direction"], "up")

    def test_no_data_at_all_gives_same(self):
        result = self._svc([]).get_week_over_week(camera_id="Gate A")
        self.assertEqual(result["direction"], "same")


class AnalyticsDailySummaryTest(unittest.TestCase):
    """get_daily_summary – aggregated daily totals."""

    def _svc(self, rows):
        return _fake_analytics_service(rows)

    def test_daily_summary_totals(self):
        today = datetime.now().astimezone().date().isoformat()
        now   = datetime.now().astimezone()
        rows = [
            _row("Gate A", "IN",  now),
            _row("Gate A", "IN",  now),
            _row("Gate A", "OUT", now),
        ]
        summary = self._svc(rows).get_daily_summary(
            camera_id="Gate A", date=today
        )
        self.assertEqual(summary["total_entries"], 2)
        self.assertEqual(summary["total_exits"],   1)
        self.assertEqual(summary["date"], today)


class AnalyticsCountHelperTest(unittest.TestCase):
    """_count_rows helper – basic counting."""

    def _svc(self):
        return _fake_analytics_service([])

    def test_counts_all_rows_without_filter(self):
        rows = [{"direction": "IN"}, {"direction": "OUT"}, {"direction": "IN"}]
        count = self._svc()._count_rows(rows)
        self.assertEqual(count, 3)

    def test_counts_only_IN(self):
        rows = [{"direction": "IN"}, {"direction": "OUT"}, {"direction": "IN"}]
        count = self._svc()._count_rows(rows, "IN")
        self.assertEqual(count, 2)

    def test_counts_only_OUT(self):
        rows = [{"direction": "IN"}, {"direction": "OUT"}]
        count = self._svc()._count_rows(rows, "OUT")
        self.assertEqual(count, 1)


# ===========================================================================
# 6. RUSH DETECTION
# ===========================================================================
class RushDetectionTest(unittest.TestCase):
    """Test the full rush-detection pipeline using a fake analytics service."""

    def _detector(self, current, mean, std):
        class FakeService:
            def get_current_count(self_, camera_id, minutes=10,
                                  table="simulated_logs", direction=None):
                return current

            def get_hourly_stats(self_, camera_id, table="simulated_logs",
                                 bucket_minutes=10, direction=None):
                return mean, std

        from backend.rush_detection import RushDetection
        return RushDetection(service=FakeService())

    # -- NORMAL (below threshold) -----------------------------------------
    def test_low_count_is_NORMAL(self):
        result = self._detector(current=5, mean=10, std=2).detect_rush("Gate A")
        self.assertEqual(result["status"], "NORMAL")
        self.assertFalse(result["is_active"])

    # -- BUSY (z between 1 and 2) ----------------------------------------
    def test_busy_when_z_score_between_1_and_2(self):
        # current=22, mean=20, std=2 → z=1.0 → BUSY
        result = self._detector(current=22, mean=20, std=2).detect_rush("Gate A")
        self.assertEqual(result["status"], "BUSY")
        self.assertFalse(result["is_active"])

    # -- RUSH ALERT: 2× average ------------------------------------------
    def test_rush_alert_when_ratio_is_2x(self):
        result = self._detector(current=24, mean=12, std=3).detect_rush("Gate A")
        self.assertEqual(result["status"], "RUSH ALERT")
        self.assertTrue(result["is_active"])

    # -- RUSH ALERT: high z-score -----------------------------------------
    def test_rush_alert_when_z_score_above_2(self):
        # current=50, mean=20, std=5 → z=6 → RUSH ALERT
        result = self._detector(current=50, mean=20, std=5).detect_rush("Gate A")
        self.assertEqual(result["status"], "RUSH ALERT")
        self.assertTrue(result["is_active"])

    # -- Baseline: count < 10 always NORMAL regardless of z ---------------
    def test_cold_start_baseline_suppresses_rush(self):
        # Even with high z-score, count < 10 should be NORMAL
        result = self._detector(current=9, mean=1, std=0.1).detect_rush("Gate A")
        self.assertEqual(result["status"], "NORMAL")
        self.assertFalse(result["is_active"])

    # -- Zero std dev (no history) ----------------------------------------
    def test_zero_std_produces_zero_z_score(self):
        from backend.rush_detection import RushDetection
        detector = RushDetection.__new__(RushDetection)
        self.assertEqual(detector.calculate_z_score(current=100, mean=10, std=0), 0)

    # -- alert_level helper -----------------------------------------------
    def test_get_alert_level_normal(self):
        from backend.rush_detection import RushDetection
        d = RushDetection.__new__(RushDetection)
        self.assertEqual(d.get_alert_level(z=0.5, ratio=1.0), "NORMAL")

    def test_get_alert_level_busy(self):
        from backend.rush_detection import RushDetection
        d = RushDetection.__new__(RushDetection)
        self.assertEqual(d.get_alert_level(z=1.5, ratio=1.2), "BUSY")

    def test_get_alert_level_rush_via_z(self):
        from backend.rush_detection import RushDetection
        d = RushDetection.__new__(RushDetection)
        self.assertEqual(d.get_alert_level(z=3.0, ratio=1.5), "RUSH ALERT")

    def test_get_alert_level_rush_via_ratio(self):
        from backend.rush_detection import RushDetection
        d = RushDetection.__new__(RushDetection)
        self.assertEqual(d.get_alert_level(z=0.5, ratio=2.5), "RUSH ALERT")


# ===========================================================================
# 7. ANALYTICS ENGINE – TABLE_MAP and SOURCE_TYPE_MAP sanity check
# ===========================================================================
class AnalyticsEngineMapTest(unittest.TestCase):
    """Ensure mode→table routing is complete and consistent."""

    def test_all_modes_map_to_a_table(self):
        from backend.analytics_engine import TABLE_MAP
        for mode in ("simulation", "simulated", "generate", "live", "stream", "audit"):
            self.assertIn(mode, TABLE_MAP, f"Mode '{mode}' missing from TABLE_MAP")

    def test_audit_mode_maps_to_audit_logs(self):
        from backend.analytics_engine import TABLE_MAP
        self.assertEqual(TABLE_MAP["audit"], "audit_logs")

    def test_live_mode_maps_to_live_logs(self):
        from backend.analytics_engine import TABLE_MAP
        self.assertEqual(TABLE_MAP["live"], "live_logs")

    def test_simulation_mode_maps_to_simulated_logs(self):
        from backend.analytics_engine import TABLE_MAP
        self.assertEqual(TABLE_MAP["simulation"], "simulated_logs")


# ===========================================================================
# 8. INTEGRATION-STYLE: analytics service + rush detection together
# ===========================================================================
class IntegrationAnalyticsRushTest(unittest.TestCase):
    """
    Simulate a real scenario: many IN events in a 10-minute window →
    rush detector should fire.
    """

    def test_rush_triggered_by_high_current_count(self):
        class FakeService:
            def get_current_count(self, camera_id, minutes=10,
                                  table="simulated_logs", direction=None):
                return 30  # simulating 30 people in 10 min window

            def get_hourly_stats(self, camera_id, table="simulated_logs",
                                 bucket_minutes=10, direction=None):
                return 10, 2  # mean=10, std=2 → ratio=3× → RUSH ALERT

        from backend.rush_detection import RushDetection
        detector = RushDetection(service=FakeService())
        result = detector.detect_rush("Gate A")

        self.assertEqual(result["status"], "RUSH ALERT")
        self.assertTrue(result["is_active"])
        self.assertEqual(result["ratio"], 3.0)

    def test_normal_traffic_does_not_trigger_rush(self):
        class FakeService:
            def get_current_count(self, camera_id, minutes=10,
                                  table="simulated_logs", direction=None):
                return 12

            def get_hourly_stats(self, camera_id, table="simulated_logs",
                                 bucket_minutes=10, direction=None):
                return 10, 2  # z = (12-10)/2 = 1.0 → BUSY not RUSH

        from backend.rush_detection import RushDetection
        detector = RushDetection(service=FakeService())
        result = detector.detect_rush("Gate A")

        self.assertNotEqual(result["status"], "RUSH ALERT")
        self.assertFalse(result["is_active"])


# ===========================================================================
if __name__ == "__main__":
    unittest.main(verbosity=2)

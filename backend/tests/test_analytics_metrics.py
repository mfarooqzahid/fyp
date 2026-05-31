import unittest
from datetime import datetime, timedelta

import backend.api as api_module
from backend.analytics_service import AnalyticsService
from backend.api import build_rush_alerts
from backend.rush_detection import RushDetection


class AnalyticsMetricsTest(unittest.TestCase):
    def setUp(self):
        self.service = AnalyticsService.__new__(AnalyticsService)
        self.now = datetime.now().astimezone().replace(hour=10, minute=20, second=0, microsecond=0)
        self.rows = [
            self.row("Gate A", "IN", self.now.replace(hour=8, minute=5)),
            self.row("Gate A", "IN", self.now.replace(hour=8, minute=15)),
            self.row("Gate A", "OUT", self.now.replace(hour=8, minute=25)),
            self.row("Gate A", "IN", self.now.replace(hour=9, minute=5)),
            self.row("Gate B", "IN", self.now.replace(hour=9, minute=10)),
            self.row("Gate B", "OUT", self.now.replace(hour=9, minute=25)),
        ]

    def row(self, camera, direction, timestamp):
        return {
            "id": len(getattr(self, "rows", [])) + 1,
            "camera_id": camera,
            "direction": direction,
            "timestamp": timestamp.isoformat(),
            "session_id": "S1",
        }

    def install_rows(self, rows):
        def query_logs(table="detections", camera_id=None, camera_ids=None, session_id=None, direction=None, date=None, start_dt=None, end_dt=None):
            result = rows
            if camera_id:
                result = [row for row in result if row["camera_id"] == camera_id]
            if camera_ids is not None:
                result = [row for row in result if row["camera_id"] in camera_ids]
            if session_id:
                result = [row for row in result if row["session_id"] == session_id]
            if direction:
                result = [row for row in result if row["direction"] == direction]
            if date:
                result = [row for row in result if row["timestamp"].startswith(date)]
            if start_dt:
                result = [row for row in result if datetime.fromisoformat(row["timestamp"]) >= start_dt]
            if end_dt:
                result = [row for row in result if datetime.fromisoformat(row["timestamp"]) <= end_dt]
            return result

        self.service._query_logs = query_logs

    def test_occupancy_and_flow_split(self):
        self.install_rows(self.rows)

        occupancy = self.service.get_realtime_occupancy(camera_id="Gate A", session_id="S1")
        flow = self.service.get_flow_split(camera_id="Gate A", session_id="S1")

        self.assertEqual(occupancy["current"], 2)
        self.assertEqual(flow["incoming"], 3)
        self.assertEqual(flow["outgoing"], 1)
        self.assertEqual(flow["incoming_percent"], 75)

    def test_peak_slots(self):
        self.install_rows(self.rows)

        peaks = self.service.get_peak_slots(camera_id="Gate A", session_id="S1", bucket_minutes=30, limit=2)

        self.assertEqual(peaks[0]["count"], 2)
        self.assertIn("8:00 AM", peaks[0]["time"])

    def test_gate_comparison_percentages(self):
        self.install_rows(self.rows)

        gates = self.service.get_gate_comparison()

        self.assertEqual(gates[0]["camera"], "Gate A")
        self.assertEqual(gates[0]["traffic"], 3)
        self.assertEqual(gates[0]["percent"], 75)

    def test_congestion_levels(self):
        rows = [
            self.row("Gate A", "IN", self.now.replace(hour=8, minute=0)),
            self.row("Gate A", "IN", self.now.replace(hour=8, minute=1)),
            self.row("Gate A", "OUT", self.now.replace(hour=8, minute=2)),
        ]
        self.install_rows(rows)

        levels = self.service.get_congestion_levels(camera_id="Gate A")

        self.assertEqual(levels[0]["current"], 1)
        self.assertEqual(levels[0]["historical_max"], 2)
        self.assertEqual(levels[0]["percent"], 50)
        self.assertEqual(levels[0]["status"], "MEDIUM")

    def test_week_over_week_delta(self):
        now = datetime.now().astimezone()
        this_week = now - timedelta(days=1)
        last_week = now - timedelta(days=8)
        rows = [
            self.row("Gate A", "IN", this_week),
            self.row("Gate A", "OUT", this_week),
            self.row("Gate A", "IN", last_week),
        ]
        self.install_rows(rows)

        comparison = self.service.get_week_over_week(camera_id="Gate A")

        self.assertEqual(comparison["current_total"], 2)
        self.assertEqual(comparison["previous_total"], 1)
        self.assertEqual(comparison["change_percent"], 100)
        self.assertEqual(comparison["direction"], "up")


class RushDetectionTest(unittest.TestCase):
    def test_detects_two_times_average_in_ten_minutes(self):
        class FakeService:
            def get_current_count(self, camera_id, minutes=10, table="simulated_logs", direction=None):
                return 24

            def get_hourly_stats(self, camera_id, table="simulated_logs", bucket_minutes=10, direction=None):
                return 12, 3

        detector = RushDetection(service=FakeService())

        result = detector.detect_rush("Gate A", minutes=10, table="simulated_logs")

        self.assertEqual(result["status"], "RUSH ALERT")
        self.assertTrue(result["is_active"])
        self.assertEqual(result["ratio"], 2)


class RushAlertsEndpointLogicTest(unittest.TestCase):
    def test_builds_alerts_for_all_sources_with_camera_ids(self):
        sources = [
            {"id": "src-1", "title": "Gate 1", "mode": "generate", "camera_id": "cam-1"},
            {"id": "src-2", "title": "Gate 2", "mode": "stream", "camera_id": "cam-2"},
            {"id": "src-3", "title": "Missing camera", "mode": "stream", "camera_id": ""},
        ]

        class FakeRushDetector:
            def __init__(self):
                self.calls = []

            def detect_rush(self, camera_id, minutes=10, table="simulated_logs"):
                self.calls.append((camera_id, minutes, table))
                is_active = camera_id == "cam-2"
                return {
                    "current": 24 if is_active else 4,
                    "mean": 12 if is_active else 8,
                    "std": 3,
                    "z": 4 if is_active else 0,
                    "ratio": 2 if is_active else 0.5,
                    "status": "RUSH ALERT" if is_active else "NORMAL",
                    "window_minutes": minutes,
                    "is_active": is_active,
                }

        detector = FakeRushDetector()

        alerts = build_rush_alerts(sources, detector)

        self.assertEqual(detector.calls, [
            ("cam-1", 10, "simulated_logs"),
            ("cam-2", 10, "live_logs"),
        ])
        self.assertEqual(len(alerts), 2)
        self.assertEqual(alerts[0]["status"], "NORMAL")
        self.assertFalse(alerts[0]["active"])
        self.assertEqual(alerts[1]["title"], "Gate 2")
        self.assertEqual(alerts[1]["status"], "RUSH ALERT")
        self.assertTrue(alerts[1]["active"])
        self.assertEqual(alerts[1]["ratio"], 2)

    def test_rush_alerts_endpoint_uses_repository_sources_and_engine_detector(self):
        class FakeRepository:
            def list_sources(self):
                return [
                    {"id": "src-1", "title": "Gate 1", "mode": "generate", "camera_id": "cam-1"},
                ]

        class FakeRushDetector:
            def detect_rush(self, camera_id, minutes=10, table="simulated_logs"):
                return {
                    "current": 30,
                    "mean": 10,
                    "std": 5,
                    "z": 4,
                    "ratio": 3,
                    "status": "RUSH ALERT",
                    "window_minutes": minutes,
                    "is_active": True,
                }

        class FakeEngine:
            rush = FakeRushDetector()

        original_engine = api_module._engine
        original_repository = api_module._source_repository
        api_module._engine = FakeEngine()
        api_module._source_repository = FakeRepository()

        try:
            response = api_module.rush_alerts()
        finally:
            api_module._engine = original_engine
            api_module._source_repository = original_repository

        self.assertEqual(response["alerts"][0]["camera_id"], "cam-1")
        self.assertEqual(response["alerts"][0]["status"], "RUSH ALERT")
        self.assertTrue(response["alerts"][0]["active"])


if __name__ == "__main__":
    unittest.main()

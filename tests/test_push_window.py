import datetime
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "push_window", Path(__file__).parents[1] / "scripts/push_window.py")
window = importlib.util.module_from_spec(spec)
spec.loader.exec_module(window)


class PushWindowTests(unittest.TestCase):
    def test_boundaries_and_weekend(self):
        cases = {
            "2026-11-23T02:30": False,
            "2026-11-23T08:49": False,
            "2026-11-23T08:50": True,
            "2026-11-23T15:20": True,
            "2026-11-23T15:21": False,
            "2026-11-23T20:49": False,
            "2026-11-23T20:50": True,
            "2026-11-23T23:59": True,
            "2026-11-24T00:00": True,
            "2026-11-24T02:30": True,
            "2026-11-24T02:31": False,
            "2026-11-27T20:50": True,
            "2026-11-28T00:00": True,
            "2026-11-28T02:30": True,
            "2026-11-28T02:31": False,
            "2026-11-28T08:50": False,
            "2026-11-28T20:50": False,
            "2026-11-29T00:00": False,
            "2026-11-29T23:59": False,
        }
        for timestamp, expected in cases.items():
            with self.subTest(timestamp=timestamp):
                now = datetime.datetime.fromisoformat(timestamp).replace(tzinfo=window.BEIJING)
                self.assertEqual(window.in_push_window(now), expected)

    def test_uses_beijing_time_for_utc_inputs(self):
        now = datetime.datetime(2026, 11, 27, 18, 30, tzinfo=datetime.timezone.utc)
        self.assertTrue(window.in_push_window(now))
        self.assertFalse(window.in_push_window(now + datetime.timedelta(minutes=1)))

    def test_publisher_skips_git_when_window_is_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            git = Path(directory) / "git"
            marker = Path(directory) / "git-called"
            git.write_text(f'#!/bin/sh\ntouch "{marker}"\nexit 88\n')
            git.chmod(0o755)
            environment = dict(os.environ, MOON_DASHBOARD_DIR="/unused", MOON_PYTHON="/bin/false")
            environment["PATH"] = directory + os.pathsep + os.environ["PATH"]
            result = subprocess.run(
                ["/bin/bash", str(Path(__file__).parents[1] / "scripts/publish_snapshot.sh")],
                env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("skipped", result.stdout)
            self.assertFalse(marker.exists())

"""Regression checks using synthetic entries and temporary storage only."""
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zoneinfo import ZoneInfo

from typer.testing import CliRunner

from time_tracker import cli
from time_tracker.models import EntryStatus, TimeEntry
from time_tracker.storage import TimeStore
from time_tracker.tracker import TimeTracker


class TimerCorrectnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = TimeStore(Path(self.temp.name))
        self.tracker = TimeTracker(self.store)

    def test_aware_running_duration(self):
        now = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)
        entry = TimeEntry(task="Synthetic", start_time=now - timedelta(seconds=60))
        self.store.save_entry(entry)
        with patch("time_tracker.models.datetime") as clock:
            clock.now.return_value = now
            self.assertEqual(self.store.get_active_entry().duration_seconds, 60)
            clock.now.assert_called_once_with(timezone.utc)

    def test_dst_elapsed_duration_and_value(self):
        zone = ZoneInfo("America/New_York")
        entry = TimeEntry(task="Synthetic", start_time=datetime(2026, 11, 1, 1, 30, tzinfo=zone),
                          end_time=datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=1),
                          status=EntryStatus.COMPLETED, billable=True, hourly_rate=10)
        self.assertEqual(entry.duration_seconds, 3600)
        self.assertEqual(entry.value, 10)

    def test_legacy_naive_duration(self):
        entry = TimeEntry(task="Synthetic", start_time=datetime(2026, 1, 1, 9),
                          end_time=datetime(2026, 1, 1, 10), paused_duration=60)
        self.assertEqual(entry.duration_seconds, 3540)

    def test_failed_serialization_preserves_history(self):
        entry = self.tracker.start("Synthetic")
        original = self.store.entries_file.read_bytes()
        with patch.object(TimeEntry, "model_dump_json", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaises(RuntimeError):
                self.store.update_entry(entry)
        self.assertEqual(self.store.entries_file.read_bytes(), original)
        self.assertEqual(TimeStore(self.store.data_dir).get_active_entry().id, entry.id)

    def test_failed_replace_preserves_history_and_cleans_temp(self):
        entry = self.tracker.start("Synthetic")
        original = self.store.entries_file.read_bytes()
        with patch("time_tracker.storage.os.replace", side_effect=OSError("synthetic failure")):
            with self.assertRaises(OSError):
                self.store.update_entry(entry)
        self.assertEqual(self.store.entries_file.read_bytes(), original)
        self.assertEqual(sorted(p.name for p in self.store.data_dir.iterdir()), ["entries.jsonl"])

    def test_failed_sync_preserves_history(self):
        entry = self.tracker.start("Synthetic")
        original = self.store.entries_file.read_bytes()
        with patch("time_tracker.storage.os.fsync", side_effect=OSError("synthetic disk failure")):
            with self.assertRaises(OSError):
                self.store.update_entry(entry)
        self.assertEqual(self.store.entries_file.read_bytes(), original)
        self.assertEqual(sorted(p.name for p in self.store.data_dir.iterdir()), ["entries.jsonl"])

    def test_successful_rewrite_round_trip(self):
        entry = self.tracker.start("Synthetic")
        self.tracker.stop("Synthetic note")
        loaded = TimeStore(self.store.data_dir).load_all_entries()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].id, entry.id)
        self.assertEqual(loaded[0].status, EntryStatus.COMPLETED)

    def test_invalid_cli_durations_do_not_write(self):
        runner = CliRunner()
        for duration in ["-1h", "1hgarbage", "1.5h30m", "1:99", "1:00:99", "1:2:3:4", "0:00", "0", "1h-30m"]:
            with self.subTest(duration=duration), patch.object(cli, "get_tracker", return_value=self.tracker):
                before = self.store.load_all_entries()
                result = runner.invoke(cli.app, ["add", "Synthetic", "--", duration])
                self.assertEqual(result.exit_code, 1, result.output)
                self.assertEqual(self.store.load_all_entries(), before)

    def test_valid_cli_duration_round_trip_and_export(self):
        runner = CliRunner()
        output = self.store.data_dir / "synthetic.json"
        with patch.object(cli, "get_tracker", return_value=self.tracker):
            result = runner.invoke(cli.app, ["add", "Synthetic", "2h30m", "-d", "2026-10-29", "-b"])
            self.assertEqual(result.exit_code, 0, result.output)
            result = runner.invoke(cli.app, ["export", str(output), "-s", "2026-10-28",
                                           "-e", "2026-10-29", "-f", "json"])
            self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue(output.exists())
        entry, = self.store.load_all_entries()
        self.assertEqual(entry.duration_seconds, 9000)
        self.assertTrue(entry.billable)

    def test_supported_durations(self):
        for duration, seconds in {"2h30m": 9000, "1.5h": 5400, "45m": 2700,
                                  "90m": 5400, "2:30:00": 9000, "2:30": 9000,
                                  "15": 900, " 2H ": 7200}.items():
            with self.subTest(duration=duration):
                self.assertEqual(self.tracker._parse_duration(duration), seconds)


if __name__ == "__main__":
    unittest.main()

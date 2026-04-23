"""Local storage for time tracking data."""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from platformdirs import user_data_dir

from .models import DailySummary, EntryStatus, TimeEntry


class TimeStore:
    """JSONL-based storage for time entries."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(user_data_dir("time-tracker", "midtowntg"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.entries_file = self.data_dir / "entries.jsonl"
        self.config_file = self.data_dir / "config.json"
    
    def save_entry(self, entry: TimeEntry) -> None:
        """Append entry to storage."""
        with open(self.entries_file, "a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")
    
    def update_entry(self, entry: TimeEntry) -> None:
        """Update an existing entry (rewrite entire file)."""
        entries = self.load_all_entries()
        # Replace entry with same ID
        entries = [e for e in entries if e.id != entry.id]
        entries.append(entry)
        self._rewrite_entries(entries)
    
    def load_all_entries(self) -> list[TimeEntry]:
        """Load all entries from storage."""
        if not self.entries_file.exists():
            return []
        
        entries = []
        with open(self.entries_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        entries.append(TimeEntry.model_validate(data))
                    except Exception:
                        continue
        return entries
    
    def get_active_entry(self) -> Optional[TimeEntry]:
        """Get currently running or paused entry."""
        entries = self.load_all_entries()
        for entry in entries:
            if entry.status in (EntryStatus.RUNNING, EntryStatus.PAUSED):
                return entry
        return None
    
    def get_entries_for_date(self, date: Optional[str] = None) -> list[TimeEntry]:
        """Get entries for a specific date (YYYY-MM-DD)."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        entries = self.load_all_entries()
        return [e for e in entries if e.start_time.strftime("%Y-%m-%d") == date]
    
    def get_entries_for_range(self, start: str, end: str) -> list[TimeEntry]:
        """Get entries for date range (inclusive)."""
        entries = self.load_all_entries()
        result = []
        for entry in entries:
            entry_date = entry.start_time.strftime("%Y-%m-%d")
            if start <= entry_date <= end:
                result.append(entry)
        return result
    
    def _rewrite_entries(self, entries: list[TimeEntry]) -> None:
        """Rewrite all entries to file."""
        with open(self.entries_file, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(entry.model_dump_json() + "\n")
    
    def get_daily_summary(self, date: Optional[str] = None) -> DailySummary:
        """Generate summary for a day."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        entries = self.get_entries_for_date(date)
        total_seconds = sum(e.duration_seconds for e in entries)
        billable_seconds = sum(
            e.duration_seconds for e in entries if e.billable
        )
        
        by_category: dict[str, int] = {}
        by_task: dict[str, int] = {}
        
        for entry in entries:
            cat = entry.category or "Uncategorized"
            by_category[cat] = by_category.get(cat, 0) + entry.duration_seconds
            by_task[entry.task] = by_task.get(entry.task, 0) + entry.duration_seconds
        
        return DailySummary(
            date=date,
            total_seconds=total_seconds,
            billable_seconds=billable_seconds,
            by_category=by_category,
            by_task=by_task,
            entries=entries
        )
    
    def archive_old_entries(self, days: int = 90) -> int:
        """Archive entries older than N days. Returns count archived."""
        cutoff = datetime.now() - timedelta(days=days)
        entries = self.load_all_entries()
        
        to_keep = []
        to_archive = []
        
        for entry in entries:
            if entry.start_time < cutoff:
                to_archive.append(entry)
            else:
                to_keep.append(entry)
        
        if to_archive:
            # Archive to separate file
            archive_file = self.data_dir / f"entries_archive_{cutoff.strftime('%Y%m')}.jsonl"
            with open(archive_file, "a", encoding="utf-8") as f:
                for entry in to_archive:
                    f.write(entry.model_dump_json() + "\n")
            
            # Rewrite active file
            self._rewrite_entries(to_keep)
        
        return len(to_archive)

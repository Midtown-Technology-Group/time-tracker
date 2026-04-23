"""Core time tracking logic."""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .models import Category, EntryStatus, TimeEntry
from .storage import TimeStore


class TimeTracker:
    """Main time tracking controller."""
    
    def __init__(self, store: Optional[TimeStore] = None):
        self.store = store or TimeStore()
        self._categories: Optional[list[Category]] = None
    
    def start(
        self,
        task: str,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        billable: bool = False,
        hourly_rate: Optional[float] = None,
    ) -> TimeEntry:
        """Start tracking time on a new task."""
        # Check for active entry
        active = self.store.get_active_entry()
        if active:
            raise RuntimeError(
                f"Already tracking '{active.task}' ({active.duration_formatted}). "
                "Stop or pause it first with 'tt stop' or 'tt pause'"
            )
        
        entry = TimeEntry(
            task=task,
            category=category,
            tags=tags or [],
            start_time=datetime.now(),
            billable=billable,
            hourly_rate=hourly_rate,
        )
        self.store.save_entry(entry)
        return entry
    
    def stop(self, notes: Optional[str] = None) -> TimeEntry:
        """Stop the current tracking session."""
        active = self.store.get_active_entry()
        if not active:
            raise RuntimeError("No active time entry. Start one with 'tt start <task>'")
        
        if active.status == EntryStatus.PAUSED:
            # Already paused, just finalize
            pass
        
        active.end_time = datetime.now()
        active.status = EntryStatus.COMPLETED
        if notes:
            active.notes = notes
        
        self.store.update_entry(active)
        return active
    
    def pause(self) -> TimeEntry:
        """Pause the current tracking session."""
        active = self.store.get_active_entry()
        if not active:
            raise RuntimeError("No active time entry")
        
        if active.status == EntryStatus.PAUSED:
            raise RuntimeError("Already paused")
        
        # Calculate elapsed since start/resume
        elapsed = (datetime.now() - active.start_time).total_seconds()
        active.paused_duration += int(elapsed)
        active.status = EntryStatus.PAUSED
        
        self.store.update_entry(active)
        return active
    
    def resume(self) -> TimeEntry:
        """Resume a paused tracking session."""
        active = self.store.get_active_entry()
        if not active:
            raise RuntimeError("No active time entry")
        
        if active.status != EntryStatus.PAUSED:
            raise RuntimeError("Entry is not paused")
        
        # Reset start time to now, keep paused_duration
        active.start_time = datetime.now()
        active.status = EntryStatus.RUNNING
        
        self.store.update_entry(active)
        return active
    
    def cancel(self) -> None:
        """Cancel current tracking without saving."""
        active = self.store.get_active_entry()
        if not active:
            raise RuntimeError("No active time entry")
        
        # Remove from storage
        entries = self.store.load_all_entries()
        entries = [e for e in entries if e.id != active.id]
        # Rewrite without cancelled entry
        self.store._rewrite_entries(entries)
    
    def status(self) -> Optional[TimeEntry]:
        """Get current tracking status."""
        return self.store.get_active_entry()
    
    def add_time(
        self,
        task: str,
        duration: str,
        category: Optional[str] = None,
        date: Optional[str] = None,
        billable: bool = False,
    ) -> TimeEntry:
        """Add time manually (e.g., '2h30m' or '1.5h')."""
        seconds = self._parse_duration(duration)
        
        if date is None:
            entry_date = datetime.now()
        else:
            entry_date = datetime.strptime(date, "%Y-%m-%d")
        
        # Create entry that starts in past and is already completed
        end_time = entry_date
        start_time = end_time - timedelta(seconds=seconds)
        
        entry = TimeEntry(
            task=task,
            category=category,
            start_time=start_time,
            end_time=end_time,
            status=EntryStatus.COMPLETED,
            billable=billable,
        )
        self.store.save_entry(entry)
        return entry
    
    def edit_entry(
        self,
        entry_id: str,
        task: Optional[str] = None,
        category: Optional[str] = None,
        billable: Optional[bool] = None,
    ) -> TimeEntry:
        """Edit an existing entry."""
        entries = self.store.load_all_entries()
        entry = next((e for e in entries if e.id == entry_id), None)
        if not entry:
            raise RuntimeError(f"Entry {entry_id} not found")
        
        if task is not None:
            entry.task = task
        if category is not None:
            entry.category = category
        if billable is not None:
            entry.billable = billable
        
        self.store.update_entry(entry)
        return entry
    
    def get_categories(self) -> list[Category]:
        """Get list of defined categories."""
        if self._categories is None:
            # Load from config or use defaults
            cats = [
                Category(name="Admin", color="blue", billable_by_default=False),
                Category(name="Client Work", color="green", billable_by_default=True),
                Category(name="Internal", color="yellow", billable_by_default=False),
                Category(name="Research", color="purple", billable_by_default=False),
                Category(name="Meetings", color="cyan", billable_by_default=True),
            ]
            self._categories = cats
        return self._categories
    
    def _parse_duration(self, duration: str) -> int:
        """Parse duration string to seconds.
        
        Supports: 2h30m, 1.5h, 45m, 90m, 2:30:00
        """
        duration = duration.strip().lower()
        total_seconds = 0
        
        # Try HH:MM:SS format
        if ":" in duration:
            parts = duration.split(":")
            if len(parts) == 2:
                hours, minutes = int(parts[0]), int(parts[1])
                total_seconds = hours * 3600 + minutes * 60
            elif len(parts) == 3:
                hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                total_seconds = hours * 3600 + minutes * 60 + seconds
            return total_seconds
        
        # Try decimal hours (1.5h)
        if "h" in duration and "." in duration.split("h")[0]:
            match = re.match(r"(\d+\.?\d*)h", duration)
            if match:
                hours = float(match.group(1))
                return int(hours * 3600)
        
        # Try combined format (2h30m)
        h_match = re.search(r"(\d+)h", duration)
        m_match = re.search(r"(\d+)m", duration)
        
        if h_match:
            total_seconds += int(h_match.group(1)) * 3600
        if m_match:
            total_seconds += int(m_match.group(1)) * 60
        
        # If just a number, assume minutes
        if total_seconds == 0 and duration.isdigit():
            total_seconds = int(duration) * 60
        
        if total_seconds == 0:
            raise ValueError(f"Could not parse duration: {duration}")
        
        return total_seconds
    
    def archive_old(self, days: int = 90) -> int:
        """Archive old entries."""
        return self.store.archive_old_entries(days)

"""Data models for time tracking."""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EntryStatus(str, Enum):
    """Status of a time entry."""
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class TimeEntry(BaseModel):
    """A single time tracking entry."""
    id: str = Field(default_factory=lambda: datetime.now().isoformat())
    task: str  # Task description or linked task ID
    category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    start_time: datetime
    end_time: Optional[datetime] = None
    paused_duration: int = 0  # seconds
    status: EntryStatus = EntryStatus.RUNNING
    notes: Optional[str] = None
    hourly_rate: Optional[float] = None  # For billable time
    billable: bool = False
    
    @property
    def duration_seconds(self) -> int:
        """Calculate total duration in seconds."""
        if self.end_time:
            elapsed = (self.end_time - self.start_time).total_seconds()
        else:
            elapsed = (datetime.now() - self.start_time).total_seconds()
        return int(elapsed - self.paused_duration)
    
    @property
    def duration_formatted(self) -> str:
        """Format duration as HH:MM:SS."""
        seconds = self.duration_seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    @property
    def value(self) -> Optional[float]:
        """Calculate monetary value if hourly rate set."""
        if self.hourly_rate:
            return (self.duration_seconds / 3600) * self.hourly_rate
        return None


class Category(BaseModel):
    """A time tracking category."""
    name: str
    color: str = "blue"
    hourly_rate: Optional[float] = None
    billable_by_default: bool = False


class DailySummary(BaseModel):
    """Summary of time tracked for a day."""
    date: str  # YYYY-MM-DD
    total_seconds: int
    billable_seconds: int
    by_category: dict[str, int]  # category -> seconds
    by_task: dict[str, int]  # task -> seconds
    entries: list[TimeEntry]
    
    @property
    def total_formatted(self) -> str:
        """Format total time."""
        hours = self.total_seconds // 3600
        minutes = (self.total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    
    @property
    def billable_formatted(self) -> str:
        """Format billable time."""
        hours = self.billable_seconds // 3600
        minutes = (self.billable_seconds % 3600) // 60
        return f"{hours}h {minutes}m"

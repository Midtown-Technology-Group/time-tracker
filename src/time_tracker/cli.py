"""Time Tracker CLI - PowerToys-style time tracking."""
from datetime import datetime, timedelta
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from .models import EntryStatus
from .storage import TimeStore
from .tracker import TimeTracker

app = typer.Typer(
    name="time-tracker",
    help="Track time on tasks with zero friction",
    rich_markup_mode="rich",
)
console = Console()


def get_tracker() -> TimeTracker:
    """Get configured tracker instance."""
    return TimeTracker()


@app.command()
def start(
    task: str = typer.Argument(..., help="Task description or name"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Task category"),
    tag: Optional[list[str]] = typer.Option(None, "--tag", "-t", help="Tags (can use multiple)"),
    billable: bool = typer.Option(False, "--billable", "-b", help="Mark as billable time"),
    rate: Optional[float] = typer.Option(None, "--rate", "-r", help="Hourly rate (for value calculation)"),
):
    """Start tracking time on a task."""
    tracker = get_tracker()
    
    try:
        entry = tracker.start(
            task=task,
            category=category,
            tags=tag,
            billable=billable,
            hourly_rate=rate,
        )
        
        cat_display = f" [dim]({category})[/dim]" if category else ""
        billable_display = " [green]$[/green]" if billable else ""
        
        console.print(f"[green]▶ Started:[/green] {task}{cat_display}{billable_display}")
        console.print(f"[dim]   ID: {entry.id[:19]}[/dim]")
        
    except RuntimeError as e:
        console.print(f"[yellow]⚠ {e}[/yellow]")
        raise typer.Exit(1)


@app.command()
def stop(
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Add notes to the entry"),
):
    """Stop the current tracking session."""
    tracker = get_tracker()
    
    try:
        entry = tracker.stop(notes=notes)
        
        cat_display = f" [dim]({entry.category})[/dim]" if entry.category else ""
        value_display = ""
        if entry.value:
            value_display = f" [green](${entry.value:.2f})[/green]"
        
        console.print(f"[red]⏹ Stopped:[/red] {entry.task}{cat_display}")
        console.print(f"[bold]   Duration:[/bold] {entry.duration_formatted}{value_display}")
        
    except RuntimeError as e:
        console.print(f"[yellow]⚠ {e}[/yellow]")
        raise typer.Exit(1)


@app.command()
def pause():
    """Pause the current tracking session."""
    tracker = get_tracker()
    
    try:
        entry = tracker.pause()
        console.print(f"[yellow]⏸ Paused:[/yellow] {entry.task}")
        console.print(f"[dim]   Elapsed so far: {entry.duration_formatted}[/dim]")
    except RuntimeError as e:
        console.print(f"[yellow]⚠ {e}[/yellow]")
        raise typer.Exit(1)


@app.command()
def resume():
    """Resume a paused tracking session."""
    tracker = get_tracker()
    
    try:
        entry = tracker.resume()
        console.print(f"[green]▶ Resumed:[/green] {entry.task}")
    except RuntimeError as e:
        console.print(f"[yellow]⚠ {e}[/yellow]")
        raise typer.Exit(1)


@app.command()
def cancel(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Cancel current tracking without saving."""
    tracker = get_tracker()
    
    active = tracker.status()
    if not active:
        console.print("[yellow]No active entry to cancel[/yellow]")
        raise typer.Exit(1)
    
    if not force:
        confirm = typer.confirm(f"Cancel tracking '{active.task}'?")
        if not confirm:
            console.print("Cancelled.")
            raise typer.Exit()
    
    tracker.cancel()
    console.print(f"[dim]Cancelled tracking for: {active.task}[/dim]")


@app.command()
def add(
    task: str = typer.Argument(..., help="Task description"),
    duration: str = typer.Argument(..., help="Duration (e.g., '2h30m', '1.5h', '45m')"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Category"),
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Date (YYYY-MM-DD, default: today)"),
    billable: bool = typer.Option(False, "--billable", "-b", help="Mark as billable"),
):
    """Add time manually (e.g., for past work)."""
    tracker = get_tracker()
    
    try:
        entry = tracker.add_time(task, duration, category, date, billable)
        
        cat_display = f" ({category})" if category else ""
        date_display = entry.start_time.strftime("%Y-%m-%d")
        
        console.print(f"[green]✓ Added:[/green] {task}{cat_display}")
        console.print(f"[dim]   {date_display} • {entry.duration_formatted}[/dim]")
        
    except (ValueError, RuntimeError) as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    watch: bool = typer.Option(False, "--watch", "-w", help="Live updating display"),
):
    """Show current tracking status."""
    tracker = get_tracker()
    active = tracker.status()
    
    if not active:
        # Show today summary instead
        today = tracker.store.get_daily_summary()
        
        table = Table(title="Today's Time", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        
        table.add_row("Total Time", today.total_formatted)
        table.add_row("Billable", f"[green]{today.billable_formatted}[/green]" if today.billable_seconds > 0 else today.billable_formatted)
        table.add_row("Entries", str(len(today.entries)))
        
        if today.by_category:
            table.add_section()
            for cat, seconds in sorted(today.by_category.items(), key=lambda x: -x[1]):
                hours = seconds / 3600
                table.add_row(f"  {cat}", f"{hours:.1f}h")
        
        console.print(table)
        console.print("\n[dim]No active tracking session[/dim]")
        console.print("[dim]Start one with: tt start <task>[/dim]")
        return
    
    if watch:
        # Live updating display
        layout = Layout()
        
        with Live(layout, refresh_per_second=1) as live:
            while True:
                active = tracker.status()
                if not active or active.status == EntryStatus.COMPLETED:
                    break
                
                duration = active.duration_formatted
                status_text = "⏸ PAUSED" if active.status == EntryStatus.PAUSED else "▶ RUNNING"
                status_color = "yellow" if active.status == EntryStatus.PAUSED else "green"
                
                panel = Panel(
                    Text(f"{duration}", style="bold cyan", justify="center"),
                    title=f"[bold]{active.task}[/bold] [{status_color}]{status_text}[/{status_color}]",
                    subtitle=f"Started {active.start_time.strftime('%H:%M')}",
                    box=box.ROUNDED,
                    border_style=status_color,
                )
                layout.update(panel)
    else:
        # Static display
        duration = active.duration_formatted
        status_text = "⏸ PAUSED" if active.status == EntryStatus.PAUSED else "▶ RUNNING"
        status_color = "yellow" if active.status == EntryStatus.PAUSED else "green"
        
        cat_display = f"\n[dim]Category:[/dim] {active.category}" if active.category else ""
        tags_display = f"\n[dim]Tags:[/dim] {', '.join(active.tags)}" if active.tags else ""
        
        console.print(Panel(
            f"[bold cyan]{duration}[/bold cyan]{cat_display}{tags_display}",
            title=f"{active.task} [{status_color}]{status_text}[/{status_color}]",
            box=box.ROUNDED,
            border_style=status_color,
        ))


@app.command()
def today(
    detail: bool = typer.Option(False, "--detail", "-d", help="Show entry details"),
):
    """Show today's time tracking summary."""
    tracker = get_tracker()
    summary = tracker.store.get_daily_summary()
    
    console.print(f"\n[bold]Time Summary for {summary.date}[/bold]\n")
    
    # Summary table
    table = Table(box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Time", justify="right")
    table.add_column("% of Total", justify="right")
    
    total_hours = summary.total_seconds / 3600
    
    table.add_row("Total Tracked", summary.total_formatted, "100%")
    if summary.billable_seconds > 0:
        bill_pct = (summary.billable_seconds / summary.total_seconds * 100) if summary.total_seconds > 0 else 0
        table.add_row("[green]Billable[/green]", f"[green]{summary.billable_formatted}[/green]", f"[green]{bill_pct:.0f}%[/green]")
        non_bill = summary.total_seconds - summary.billable_seconds
        non_bill_h = non_bill // 3600
        non_bill_m = (non_bill % 3600) // 60
        table.add_row("[dim]Non-Billable[/dim]", f"[dim]{non_bill_h}h {non_bill_m}m[/dim]", f"[dim]{100-bill_pct:.0f}%[/dim]")
    
    console.print(table)
    
    # Category breakdown
    if summary.by_category:
        console.print("\n[bold]By Category[/bold]")
        cat_table = Table(box=box.ROUNDED)
        cat_table.add_column("Category", style="cyan")
        cat_table.add_column("Time", justify="right")
        cat_table.add_column("Bar", width=20)
        
        max_seconds = max(summary.by_category.values())
        
        for cat, seconds in sorted(summary.by_category.items(), key=lambda x: -x[1]):
            hours = seconds / 3600
            bar_len = int((seconds / max_seconds) * 20) if max_seconds > 0 else 0
            bar = "█" * bar_len + "░" * (20 - bar_len)
            cat_table.add_row(cat, f"{hours:.1f}h", bar)
        
        console.print(cat_table)
    
    # Entry details
    if detail and summary.entries:
        console.print("\n[bold]Entries[/bold]")
        entry_table = Table(box=box.ROUNDED)
        entry_table.add_column("Time")
        entry_table.add_column("Task")
        entry_table.add_column("Category")
        entry_table.add_column("Duration", justify="right")
        
        for entry in summary.entries:
            start_str = entry.start_time.strftime("%H:%M")
            cat_str = entry.category or "-"
            billable_mark = " [green]$[/green]" if entry.billable else ""
            entry_table.add_row(
                start_str,
                entry.task,
                cat_str,
                f"{entry.duration_formatted}{billable_mark}"
            )
        
        console.print(entry_table)


@app.command()
def week(
    offset: int = typer.Option(0, "--offset", "-o", help="Weeks ago (0=this week, 1=last week)"),
):
    """Show weekly time summary."""
    tracker = get_tracker()
    
    # Calculate week range
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday() + (offset * 7))
    
    console.print(f"\n[bold]Week of {start_of_week.strftime('%Y-%m-%d')}[/bold]\n")
    
    # Get daily summaries for the week
    daily_totals = []
    total_seconds = 0
    billable_seconds = 0
    
    for i in range(7):
        date = (start_of_week + timedelta(days=i)).strftime("%Y-%m-%d")
        summary = tracker.store.get_daily_summary(date)
        daily_totals.append((date, summary))
        total_seconds += summary.total_seconds
        billable_seconds += summary.billable_seconds
    
    # Week summary
    total_h = total_seconds // 3600
    total_m = (total_seconds % 3600) // 60
    bill_h = billable_seconds // 3600
    bill_m = (billable_seconds % 3600) // 60
    
    table = Table(box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    
    table.add_row("Total Hours", f"{total_h}h {total_m}m")
    if billable_seconds > 0:
        table.add_row("[green]Billable[/green]", f"[green]{bill_h}h {bill_m}m[/green]")
    
    console.print(table)
    
    # Daily breakdown
    console.print("\n[bold]Daily Breakdown[/bold]")
    day_table = Table(box=box.ROUNDED)
    day_table.add_column("Day")
    day_table.add_column("Date")
    day_table.add_column("Total", justify="right")
    day_table.add_column("Billable", justify="right")
    day_table.add_column("Bar", width=20)
    
    max_day = max((s.total_seconds for _, s in daily_totals), default=0)
    
    for date, summary in daily_totals:
        dt = datetime.strptime(date, "%Y-%m-%d")
        day_name = dt.strftime("%a")
        
        hours = summary.total_seconds / 3600
        bar_len = int((summary.total_seconds / max_day) * 20) if max_day > 0 else 0
        bar = "█" * bar_len + "░" * (20 - bar_len)
        
        bill_str = f"{summary.billable_seconds // 3600}h" if summary.billable_seconds > 0 else "-"
        
        day_table.add_row(
            day_name,
            date,
            summary.total_formatted,
            f"[green]{bill_str}[/green]" if summary.billable_seconds > 0 else bill_str,
            bar
        )
    
    console.print(day_table)


@app.command()
def list(
    date: Optional[str] = typer.Option(None, "--date", "-d", help="List entries for date (default: today)"),
    days: int = typer.Option(1, "--days", "-n", help="Number of days to show"),
):
    """List time entries."""
    tracker = get_tracker()
    
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    entries = []
    for i in range(days):
        check_date = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=i)).strftime("%Y-%m-%d")
        entries.extend(tracker.store.get_entries_for_date(check_date))
    
    if not entries:
        console.print("[dim]No entries found[/dim]")
        return
    
    table = Table(title=f"Time Entries", box=box.ROUNDED)
    table.add_column("Date", style="cyan", width=12)
    table.add_column("Start")
    table.add_column("Task")
    table.add_column("Category")
    table.add_column("Duration", justify="right")
    table.add_column("Status")
    
    for entry in sorted(entries, key=lambda e: e.start_time, reverse=True):
        date_str = entry.start_time.strftime("%Y-%m-%d")
        start_str = entry.start_time.strftime("%H:%M")
        status_str = "[green]●[/green]" if entry.status == EntryStatus.RUNNING else "[dim]✓[/dim]"
        if entry.status == EntryStatus.PAUSED:
            status_str = "[yellow]⏸[/yellow]"
        
        cat_str = entry.category or "-"
        billable_mark = " [green]$[/green]" if entry.billable else ""
        
        table.add_row(
            date_str,
            start_str,
            entry.task,
            cat_str,
            f"{entry.duration_formatted}{billable_mark}",
            status_str
        )
    
    console.print(table)


@app.command()
def export(
    output: str = typer.Argument(..., help="Output file path"),
    start_date: Optional[str] = typer.Option(None, "--start", "-s", help="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, "--end", "-e", help="End date (YYYY-MM-DD)"),
    format: str = typer.Option("csv", "--format", "-f", help="Export format (csv, json)"),
):
    """Export time entries to file."""
    import csv
    import json as json_lib
    
    tracker = get_tracker()
    
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    entries = tracker.store.get_entries_for_range(start_date, end_date)
    
    if not entries:
        console.print("[yellow]No entries found for date range[/yellow]")
        raise typer.Exit(1)
    
    if format.lower() == "json":
        data = [e.model_dump() for e in entries]
        with open(output, "w", encoding="utf-8") as f:
            json_lib.dump(data, f, indent=2, default=str)
    else:  # csv
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Task", "Category", "Tags", "Duration", "Billable", "Notes"])
            for e in entries:
                writer.writerow([
                    e.start_time.strftime("%Y-%m-%d"),
                    e.task,
                    e.category or "",
                    ", ".join(e.tags),
                    e.duration_formatted,
                    "Yes" if e.billable else "No",
                    e.notes or ""
                ])
    
    console.print(f"[green]✓ Exported {len(entries)} entries to {output}[/green]")


@app.command()
def archive(
    days: int = typer.Option(90, "--days", "-d", help="Archive entries older than N days"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be archived"),
):
    """Archive old entries to keep active storage fast."""
    tracker = get_tracker()
    
    if dry_run:
        # Count without archiving
        entries = tracker.store.load_all_entries()
        cutoff = datetime.now() - timedelta(days=days)
        old_count = sum(1 for e in entries if e.start_time < cutoff)
        console.print(f"[dim]Would archive {old_count} entries older than {days} days[/dim]")
    else:
        count = tracker.archive_old(days)
        if count > 0:
            console.print(f"[green]✓ Archived {count} entries[/green]")
        else:
            console.print("[dim]No entries to archive[/dim]")


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()

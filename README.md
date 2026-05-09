# Time Tracker

> ⏱️ Track time on tasks with zero friction. A PowerToys-style CLI for MSP workflows.

Time Tracker is a lightweight, keyboard-first time tracking tool that integrates with your GTD workflow. No web interfaces, no complex setups—just quick commands that keep you in flow.

## Quick Start

```powershell
# Start tracking
$ tt start "Client server maintenance" --category "Client Work" --billable
▶ Started: Client server maintenance (Client Work) $
   ID: 2025-01-15T08:30:00

# Check status anytime
$ tt status
┌─ Client server maintenance [green]▶ RUNNING[/green] ─┐
│ [bold cyan]01:23:45[/bold cyan]                                    │
└──────────────────────────────────────────┘

# Stop when done
$ tt stop --notes "Completed backup and patch cycle"
⏹ Stopped: Client server maintenance
   Duration: 02:15:30 ($281.25)

# See your day
$ tt today
Time Summary for 2025-01-15

┌───────────────┬──────────┬──────────┐
│ Metric        │    Time  │% of Total│
├───────────────┼──────────┼──────────┤
│ Total Tracked │ 6h 45m   │     100% │
│ [green]Billable[/green]     │ [green]4h 30m[/green]   │  [green]67%[/green]    │
│ [dim]Non-Billable[/dim] │ [dim]2h 15m[/dim]  │  [dim]33%[/dim]    │
└───────────────┴──────────┴──────────┘
```

## Installation

### Option 1: pip install (Recommended)
```powershell
pip install time-tracker
```

### Option 2: Run from source
```powershell
git clone https://github.com/Midtown-Technology-Group/time-tracker.git
cd time-tracker
.\invoke.ps1 --help
```

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `start` | Begin tracking a task | `tt start "Task name" -c Category -b` |
| `stop` | End current session | `tt stop -n "Notes"` |
| `pause` / `resume` | Pause and resume | `tt pause` |
| `cancel` | Discard current session | `tt cancel` |
| `add` | Log past time manually | `tt add "Task" 2h30m -d 2025-01-14` |
| `status` | Show current timer | `tt status --watch` |
| `today` | Daily summary | `tt today --detail` |
| `week` | Weekly summary | `tt week -o 1` |
| `list` | Show entries | `tt list -n 7` |
| `export` | Export to CSV/JSON | `tt export timesheet.csv -s 2025-01-01` |
| `archive` | Clean old data | `tt archive --days 90` |

## Keyboard Shortcuts (PowerToys-style)

Set up aliases for instant access:

```powershell
# Add to your PowerShell profile
function ts { tt start $args }
function tp { tt pause }
function tr { tt resume }
function tx { tt stop }
function td { tt today }

# Now use them anywhere:
$ ts "Quick task" -b    # Start billable task
$ tx                     # Stop tracking
$ td                     # See today's summary
```

## Categories & Billable Time

Pre-configured categories with colors:
- **Admin** (blue) - Internal admin work
- **Client Work** (green) - Billable client time
- **Internal** (yellow) - Company internal projects
- **Research** (purple) - Learning and research
- **Meetings** (cyan) - Scheduled meetings

Mark time as billable:
```powershell
$ tt start "Network audit" --category "Client Work" --billable --rate 125
```

## Data Storage

Time entries are stored locally in:
- Windows: `%LOCALAPPDATA%\midtowntg\time-tracker\entries.jsonl`
- Linux/macOS: `~/.local/share/time-tracker/entries.jsonl`

JSONL format = human-readable, append-only, easy to backup or sync.

## Integration with GTD

Time Tracker works alongside your existing GTD setup:

```powershell
# In your daily-startup.ps1 script:
# 1. Sync context
& "C:\Tools\context-sync\invoke.ps1"

# 2. See what's waiting
& "C:\Tools\gtd-dashboard\invoke.ps1" now

# 3. Track time on your first task
& "C:\Tools\time-tracker\invoke.ps1" start "Review overnight alerts" -c Admin
```

## Why JSONL?

Time Tracker uses [JSON Lines](https://jsonlines.org/) format because:
- **Append-only** = fast writes, no file locks
- **Human-readable** = easy to inspect or edit
- **Line-oriented** = easy to grep, tail, stream
- **Standard** = import into any analytics tool

## Export Formats

### CSV (default)
```powershell
$ tt export january-billable.csv -s 2025-01-01 -e 2025-01-31
# Date, Task, Category, Tags, Duration, Billable, Notes
```

### JSON
```powershell
$ tt export backup.json --format json -s 2025-01-01
# Full structured data for custom processing
```

## License

AGPL-3.0 - Open source, always.

---

Built by [Midtown Technology Group](https://midtowntg.com) for MSP workflows.

## Windows MSI

Tagged releases build a per-machine Windows MSI that installs `time-tracker.exe` under `Program Files` and adds that install directory to the system PATH. Installing or uninstalling the MSI requires an elevated prompt.

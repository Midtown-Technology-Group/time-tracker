# Time Tracker

This Python 3.10+ CLI records local MSP task time, billable categories, notes, and summaries. Read [README.md](README.md) for commands and storage. `src/time_tracker` is the packaged code; `tt` and `time-tracker` map to `time_tracker.cli:main`; `invoke.ps1` is the documented Windows wrapper; it can prefer an installed package over checkout source.

Keep timer transitions (`start`, `stop`, `pause`, `resume`, `cancel`), manual time entry, billable rate calculations, and date-filtered exports compatible. Inspect persistence and CLI behavior together when changing time accounting. Preserve JSONL records and historical billable meaning; validate migration and recovery before changing schemas or file locations.

Use synthetic entries and an isolated temporary data directory for development checks. Real entries live under `%LOCALAPPDATA%/midtowntg/time-tracker/entries.jsonl` on Windows and `~/.local/share/time-tracker/entries.jsonl` on Linux/macOS. Never cancel a live timer, archive history, or overwrite/export private time records as a source verification shortcut.

`pyproject.toml` declares Hatchling packaging and optional Graph dependencies, but no development test extra or configured test gate. Do not invent a pytest requirement. Inspect existing tests and workflow checks for the affected change; document a focused synthetic behavior check and the absence of an established gate when applicable. The README's `./invoke.ps1 --help` is the documented source entry-point smoke check; use it only in an isolated editable-checkout environment and confirm the imported `time_tracker` module resolves to this checkout. A successful wrapper call against an installed package does not verify source edits.

Windows MSI packaging/release is driven by `.github/workflows/release-msi.yml`; a source edit does not authorize publishing or installing it. Graph integration also requires the intended account, scopes, and action authorization. Keep customer names, work notes, rates, and exported timesheets out of committed fixtures and logs. Report verified source behavior separately from released binaries or live business records.

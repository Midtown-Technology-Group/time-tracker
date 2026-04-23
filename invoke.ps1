# find the script directory (where invoke.ps1 lives)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# check for virtual environment first
if ($env:VIRTUAL_ENV) {
    $pythonCmd = "python"
} else {
    # find Python on the system
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
    }
    
    if (-not $pythonCmd) {
        Write-Error "Python not found. Please install Python 3.10+ or activate a virtual environment."
        exit 1
    }
    
    $pythonCmd = $pythonCmd.Source
}

# check if time_tracker module is available (pip installed)
$moduleCheck = & $pythonCmd -c "import time_tracker" 2>&1
if ($LASTEXITCODE -ne 0) {
    # try with src directory (running from source)
    $srcDir = Join-Path $scriptDir "src"
    if (Test-Path $srcDir) {
        $env:PYTHONPATH = "$srcDir;$env:PYTHONPATH"
    } else {
        Write-Error "time_tracker module not found and no src/ directory. Run 'pip install -e .' or check your installation."
        exit 1
    }
}

# run the CLI with all arguments passed through
& $pythonCmd -m time_tracker.cli @args

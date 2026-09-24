# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
# การแยกชั้น (เจ้าของระบบ 15 ก.ย. 2026): เทรดคอร์ (ไม่ใช้ LLM) แยกจากชั้นวิจัย (LLM)
#   Start/Stop          = ทั้งระบบ (เดิม)
#   TraderStart/Stop    = เฉพาะตัวเทรด + audit (ไม่แตะงานวิจัย/LLM)
#   ResearchPause/Resume= เฉพาะงานวิจัย/LLM (ไม่แตะตัวเทรด)
param([ValidateSet('Start','Stop','TraderStart','TraderStop','ResearchPause','ResearchResume')][string]$Action)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$taskProject = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$taskPython = Join-Path $taskProject '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Install the project Python environment first.' }
$taskMode = Join-Path $PSScriptRoot 'choose_mode.py'
if ($Action -eq 'TraderStart') {
    if (Test-Path -LiteralPath (Join-Path $taskProject 'work\AUTO_TRADER_STOP')) {
        throw 'Kill switch present. Explicitly authorize restart (clear_kill_switch.ps1) before starting.'
    }
    & (Join-Path $PSScriptRoot 'start_auto_trader.ps1')
    Write-Output 'Trader + audit started (research/LLM untouched).'
    exit 0
}
if ($Action -eq 'TraderStop') {
    & (Join-Path $PSScriptRoot 'stop_auto_trader.ps1')
    Write-Output 'Trader + audit stopped (research/LLM untouched).'
    exit 0
}
if ($Action -eq 'ResearchPause') {
    & $taskPython $taskMode --pause-all
    if ($LASTEXITCODE -ne 0) { throw 'Could not pause research jobs.' }
    Write-Output 'Research/LLM jobs paused; trader untouched.'
    exit 0
}
if ($Action -eq 'ResearchResume') {
    & $taskPython $taskMode --resume
    if ($LASTEXITCODE -ne 0) { throw 'Research resume failed.' }
    Write-Output 'Research/LLM jobs resumed; trader untouched.'
    exit 0
}
if ($Action -eq 'Stop') {
    $taskErrors = @()
    try { & (Join-Path $PSScriptRoot 'stop_auto_trader.ps1') } catch { $taskErrors += $_.Exception.Message }
    & $taskPython $taskMode --pause-all
    if ($LASTEXITCODE -ne 0) { $taskErrors += 'Could not pause all research and AI bot jobs.' }
    if ($taskErrors.Count) { throw ($taskErrors -join '; ') }
    Write-Output 'Trader stopped; all research and AI bot jobs paused.'
    exit 0
}
& $taskPython $taskMode --print-mode
if ($LASTEXITCODE -ne 0) {
    & $taskPython $taskMode
    if ($LASTEXITCODE -ne 0) { throw 'Mode selection cancelled or failed; nothing started.' }
}
if (Test-Path -LiteralPath (Join-Path $taskProject 'work\AUTO_TRADER_STOP')) {
    throw 'Kill switch present. Explicitly authorize restart and clear it before starting.'
}
if (-not $env:HERMES_EXE) {
    $taskHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { Join-Path $env:LOCALAPPDATA 'hermes' }
    $env:HERMES_EXE = Join-Path $taskHome 'hermes-agent\venv\Scripts\hermes.exe'
}
$taskGateway = & $env:HERMES_EXE gateway status 2>&1
if ($LASTEXITCODE -ne 0 -or ($taskGateway -join ' ') -notmatch 'Gateway process running') {
    throw 'Hermes gateway is not running. Start the configured gateway first; trader not started.'
}
try {
    & (Join-Path $PSScriptRoot 'start_auto_trader.ps1')
    & $taskPython $taskMode --resume
    if ($LASTEXITCODE -ne 0) { throw 'Research resume failed.' }
} catch {
    & $taskPython $taskMode --pause-all
    & (Join-Path $PSScriptRoot 'stop_auto_trader.ps1')
    throw
}
Write-Output 'Trader and research started successfully in the selected mode.'

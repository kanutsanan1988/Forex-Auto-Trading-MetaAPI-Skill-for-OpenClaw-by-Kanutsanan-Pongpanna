# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'

$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$python = Join-Path $project '.venv\Scripts\python.exe'
$trader = Join-Path $PSScriptRoot 'auto_trader.py'
$configPath = Join-Path $PSScriptRoot 'auto_config.json'
$work = Join-Path $project 'work'
$stopFile = Join-Path $work 'AUTO_TRADER_STOP'
$pidFile = Join-Path $work 'auto_trader_supervisor.pid'
$lockFile = Join-Path $work 'auto_trader_supervisor.lock'
$logFile = Join-Path $work 'auto_trader_supervisor.log'

New-Item -ItemType Directory -Force -Path $work | Out-Null
$lockStream = $null
try {
    $lockStream = [System.IO.File]::Open(
        $lockFile,
        [System.IO.FileMode]::OpenOrCreate,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
} catch {
    Add-Content -LiteralPath $logFile -Encoding UTF8 -Value "$(Get-Date -Format o) supervisor already running"
    exit 2
}

try {
    Set-Content -LiteralPath $pidFile -Encoding ASCII -Value $PID
    while (-not (Test-Path -LiteralPath $stopFile)) {
        $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
        if (-not $config.live_enabled) {
            Add-Content -LiteralPath $logFile -Encoding UTF8 -Value "$(Get-Date -Format o) live_enabled=false; supervisor stopped"
            break
        }
        & $python $trader --live
        $exitCode = $LASTEXITCODE
        Add-Content -LiteralPath $logFile -Encoding UTF8 -Value "$(Get-Date -Format o) auto_trader exit=$exitCode"
        if (Test-Path -LiteralPath $stopFile) { break }
        Start-Sleep -Seconds ([int]$config.reconnect_seconds)
    }
} finally {
    if (Test-Path -LiteralPath $pidFile) {
        $recordedPid = (Get-Content -LiteralPath $pidFile -Raw).Trim()
        if ($recordedPid -eq [string]$PID) { Remove-Item -LiteralPath $pidFile -Force }
    }
    if ($lockStream) { $lockStream.Dispose() }
}

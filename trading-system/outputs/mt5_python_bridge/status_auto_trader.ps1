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
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$work = Join-Path $project 'work'
$config = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'auto_config.json') -Raw | ConvertFrom-Json
$stopFile = Join-Path $work 'AUTO_TRADER_STOP'
$traderPidFile = Join-Path $work 'auto_trader.pid'
$supervisorPidFile = Join-Path $work 'auto_trader_supervisor.pid'
$auditFile = Join-Path $work 'auto_trader_audit.jsonl'

function Read-ProcessState($path) {
    if (-not (Test-Path -LiteralPath $path)) { return @{ pid = $null; running = $false } }
    $processId = [int](Get-Content -LiteralPath $path -Raw)
    return @{ pid = $processId; running = [bool](Get-Process -Id $processId -ErrorAction SilentlyContinue) }
}

$trader = Read-ProcessState $traderPidFile
$supervisor = Read-ProcessState $supervisorPidFile
[pscustomobject]@{
    LiveEnabled = [bool]$config.live_enabled
    KillSwitch = Test-Path -LiteralPath $stopFile
    TraderPID = $trader.pid
    TraderRunning = $trader.running
    SupervisorPID = $supervisor.pid
    SupervisorRunning = $supervisor.running
} | Format-List
if (Test-Path -LiteralPath $auditFile) {
    Write-Output 'Latest audit events:'
    Get-Content -LiteralPath $auditFile -Tail 5
}

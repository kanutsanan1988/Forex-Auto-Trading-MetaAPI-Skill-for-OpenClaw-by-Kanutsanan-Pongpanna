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
$stopFile = Join-Path $work 'AUTO_TRADER_STOP'
$traderPidFile = Join-Path $work 'auto_trader.pid'
$supervisorPidFile = Join-Path $work 'auto_trader_supervisor.pid'

New-Item -ItemType Directory -Force -Path $work | Out-Null
Set-Content -LiteralPath $stopFile -Encoding UTF8 -Value "Stopped by operator at $(Get-Date -Format o)"

$deadline = (Get-Date).AddSeconds(30)
while (((Test-Path -LiteralPath $traderPidFile) -or (Test-Path -LiteralPath $supervisorPidFile)) -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
}

# If a process did not honor the kill switch in time, terminate only the
# exact PIDs recorded by this system. This prevents restart loops while
# avoiding any broad process termination.
foreach ($pidPath in @($traderPidFile, $supervisorPidFile)) {
    if (-not (Test-Path -LiteralPath $pidPath)) { continue }
    $rawPid = (Get-Content -LiteralPath $pidPath -Raw).Trim()
    $targetPid = 0
    if (-not [int]::TryParse($rawPid, [ref]$targetPid)) { continue }
    $process = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 300
    }
    if (Test-Path -LiteralPath $pidPath) {
        Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
    }
}
Write-Output "Kill switch created: $stopFile"
Write-Output ('Trader stopped=' + (-not (Test-Path -LiteralPath $traderPidFile)))
Write-Output ('Supervisor stopped=' + (-not (Test-Path -LiteralPath $supervisorPidFile)))

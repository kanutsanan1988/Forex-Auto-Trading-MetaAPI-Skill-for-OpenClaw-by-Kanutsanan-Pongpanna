# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$stopFile = Join-Path $project 'work\AUTO_TRADER_STOP'
$traderPidFile = Join-Path $project 'work\auto_trader.pid'
$supervisorPidFile = Join-Path $project 'work\auto_trader_supervisor.pid'

if ((Test-Path -LiteralPath $traderPidFile) -or (Test-Path -LiteralPath $supervisorPidFile)) {
    throw 'Refusing to clear the kill switch while trader or supervisor PID files exist'
}
if (Test-Path -LiteralPath $stopFile) {
    Remove-Item -LiteralPath $stopFile -Force
    Write-Output "Kill switch cleared: $stopFile"
} else {
    Write-Output 'Kill switch is already clear'
}

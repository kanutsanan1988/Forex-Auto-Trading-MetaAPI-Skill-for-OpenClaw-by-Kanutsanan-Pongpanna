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
#
# การแก้ไข 19 ก.ย. 2026 (แก้ปัญหาปุ่มเปิดระบบใช้ไม่ได้):
#   อาการเดิม: Start-Process -WindowStyle Hidden ล้มด้วย exit -1073741502 (0xC0000142)
#   สาเหตุ: การ spawn โปรเซสลูกจาก session ที่สภาพแวดล้อมไม่สมบูรณ์บนเครื่องนี้
#   วิธีแก้: ใช้ Task Scheduler เป็นวิธีหลัก (เป็นวิธีที่ Hermes gateway บนเครื่องนี้ใช้ได้ผล)
#   และตรวจความสำเร็จจากไฟล์ work\auto_trader_supervisor.pid (หลักฐานจริง) ไม่ใช่ exit code
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'

$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$work = Join-Path $project 'work'
$stopFile = Join-Path $work 'AUTO_TRADER_STOP'
$pidFile = Join-Path $work 'auto_trader_supervisor.pid'
$configPath = Join-Path $PSScriptRoot 'auto_config.json'
$supervisor = Join-Path $PSScriptRoot 'auto_trader_supervisor.ps1'
$taskName = 'GoldTraderSupervisor'

if (Test-Path -LiteralPath $stopFile) {
    throw "Kill switch exists: $stopFile. Review it before removing and restarting."
}
$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
if (-not $config.live_enabled) { throw 'live_enabled is false in auto_config.json' }
if (Test-Path -LiteralPath $pidFile) {
    $existingPid = 0
    if ([int]::TryParse((Get-Content -LiteralPath $pidFile -Raw).Trim(), [ref]$existingPid)) {
        if (Get-Process -Id $existingPid -ErrorAction SilentlyContinue) {
            throw "Supervisor is already running with PID $existingPid"
        }
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

$hostExecutable = (Get-Process -Id $PID).Path
if (-not $hostExecutable) {
    $hostExecutable = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
}
$arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $supervisor + '"'))
$cmdLine = '"' + $hostExecutable + '" ' + ($arguments -join ' ')

# รอให้ซูเปอร์ไวเซอร์เขียนไฟล์ PID ของตัวเอง = หลักฐานว่าขึ้นจริง
function Wait-SupervisorStarted([int]$seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $pidFile) {
            $sp = 0
            if ([int]::TryParse((Get-Content -LiteralPath $pidFile -Raw).Trim(), [ref]$sp)) {
                if (Get-Process -Id $sp -ErrorAction SilentlyContinue) { return $sp }
            }
        }
        Start-Sleep -Milliseconds 400
    }
    return 0
}

$startedPid = 0
$errors = @()

# วิธีที่ 1: Task Scheduler (วิธีที่ได้ผลจริงบนเครื่องนี้ — ใช้ session ของผู้ใช้)
# ใช้ cmdlet Register-ScheduledTask/Start-ScheduledTask แทน schtasks.exe
# เพราะ path ของโปรเจกต์มีช่องว่างและอักษรไทย ทำให้ schtasks ตัดอาร์กิวเมนต์ผิด
if (-not $startedPid) {
    try {
        $taskArgument = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $supervisor + '"'
        $taskAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $taskArgument
        $taskTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddYears(5)
        $taskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $taskTrigger `
            -Settings $taskSettings -Force -ErrorAction Stop | Out-Null
        Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
        $startedPid = Wait-SupervisorStarted 15
        if (-not $startedPid) { $errors += 'Task Scheduler' }
    } catch {
        $errors += "Task Scheduler: $($_.Exception.Message)"
    }
}

# วิธีที่ 2: Start-Process (สำรอง — ใช้ได้บนเครื่องทั่วไป)
if (-not $startedPid) {
    try {
        $process = Start-Process -FilePath $hostExecutable -ArgumentList $arguments -WindowStyle Hidden -PassThru
        $startedPid = Wait-SupervisorStarted 6
        if (-not $startedPid) {
            $code = if ($process.HasExited) { $process.ExitCode } else { 'no-pid-file' }
            $errors += "Start-Process (exit=$code)"
        }
    } catch {
        $errors += "Start-Process: $($_.Exception.Message)"
    }
}

# วิธีที่ 3: WMI Win32_Process.Create (สำรอง)
if (-not $startedPid) {
    try {
        $res = Invoke-CimMethod -ClassName Win32_Process -MethodName Create `
            -Arguments @{ CommandLine = $cmdLine; CurrentDirectory = $PSScriptRoot }
        $startedPid = Wait-SupervisorStarted 8
        if (-not $startedPid) { $errors += "WMI Create (return=$($res.ReturnValue))" }
    } catch {
        $errors += "WMI: $($_.Exception.Message)"
    }
}

if (-not $startedPid) {
    throw ("Supervisor start failed (all methods tried): " + ($errors -join ' | ') +
           " - try running this in a visible PowerShell window: powershell -NoProfile -ExecutionPolicy Bypass -File `"$supervisor`"")
}
Write-Output "Auto trader supervisor started. PID=$startedPid"

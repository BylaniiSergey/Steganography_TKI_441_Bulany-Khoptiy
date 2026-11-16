# Запускает Octave GUI со сценарием steps.m и параллельно снимает окна (capture_windows.ps1).
# Скрипт должен оставаться запущенным, пока идёт съёмка: дочерние процессы закрываются вместе с ним.
param([string]$ShotDir, [int]$MaxMinutes = 25)

$root = "C:\Users\user\Octave\octave-11.3.0-w64"
$mg = "$root\mingw64"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$work = Join-Path $here "work"
$cap = Join-Path $here "capture_windows.ps1"

if (Test-Path $ShotDir) { Remove-Item $ShotDir -Recurse -Force }
New-Item -ItemType Directory $ShotDir | Out-Null
Remove-Item (Join-Path $work "monkey_barrel.png") -Force -ErrorAction SilentlyContinue

# окружение как в официальном запускателе octave.vbs
$env:PATH = "$root\usr\bin;$mg\bin;$mg\qt6\bin;" + $env:PATH
$env:QT_PLUGIN_PATH = "$mg\qt6\plugins"
$env:MSYSTEM = "MINGW64"; $env:TERM = "cygwin"; $env:GNUTERM = "wxt"; $env:HOME = $env:USERPROFILE
$env:SHOTDIR = ($ShotDir -replace '\\', '/')

$capProc = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$cap`"", "-Dir", "`"$ShotDir`"", "-ProcName", "octave-gui", "-Timeout", ($MaxMinutes * 60)) -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 2
$oct = Start-Process -FilePath "$mg\bin\octave-gui.exe" -ArgumentList @("--persist", "steps.m") -WorkingDirectory $work -PassThru
"octave pid $($oct.Id), capture pid $($capProc.Id)"

$deadline = (Get-Date).AddMinutes($MaxMinutes)
while ((Get-Date) -lt $deadline) {
  if (Test-Path (Join-Path $ShotDir "stop.txt")) { break }
  if ($oct.HasExited) { "octave exited early, code $($oct.ExitCode)"; break }
  Start-Sleep -Seconds 3
}
Start-Sleep -Seconds 3
"files: " + (Get-ChildItem $ShotDir -Filter "shot_*.png").Count
try { if (-not $oct.HasExited) { Stop-Process -Id $oct.Id -Force } } catch {}
try { if (-not $capProc.HasExited) { Stop-Process -Id $capProc.Id -Force } } catch {}
"finished"

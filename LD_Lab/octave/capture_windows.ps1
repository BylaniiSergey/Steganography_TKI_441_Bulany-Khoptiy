# Снимает окна процесса Octave (главное окно и окна фигур) по запросам из Octave.
# Octave создаёт файл req_NN.txt, этот скрипт делает снимки окон в shot_NN_<окно>.png и создаёт ok_NN.txt.
# Запуск: powershell -File capture_windows.ps1 -Dir <папка_обмена> -ProcName octave-gui -Timeout 900
param([string]$Dir, [string]$ProcName = "octave-gui", [int]$Timeout = 900)

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Collections.Generic;
public class WinCap {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  public static List<IntPtr> ForPids(HashSet<uint> pids) {
    var res = new List<IntPtr>();
    EnumWindows((h, l) => {
      uint pid; GetWindowThreadProcessId(h, out pid);
      if (pids.Contains(pid) && IsWindowVisible(h) && !IsIconic(h)) {
        var sb = new StringBuilder(256); GetWindowText(h, sb, 256);
        if (sb.Length > 0) res.Add(h);
      }
      return true;
    }, IntPtr.Zero);
    return res;
  }
  public static string Title(IntPtr h) { var sb = new StringBuilder(256); GetWindowText(h, sb, 256); return sb.ToString(); }
}
"@

[void][WinCap]::SetProcessDPIAware()   # иначе размеры окон занижаются при масштабе экрана > 100 %

function Save-Window($h, $path) {
  $r = New-Object WinCap+RECT
  [void][WinCap]::GetWindowRect($h, [ref]$r)
  $w = $r.R - $r.L; $hh = $r.B - $r.T
  if ($w -lt 50 -or $hh -lt 50) { return $false }
  $bmp = New-Object System.Drawing.Bitmap $w, $hh
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $hdc = $g.GetHdc()
  $ok = [WinCap]::PrintWindow($h, $hdc, 2)
  $g.ReleaseHdc($hdc)
  $g.Dispose()
  $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $bmp.Dispose()
  return $ok
}

$deadline = (Get-Date).AddSeconds($Timeout)
$done = @{}
while ((Get-Date) -lt $deadline) {
  foreach ($req in Get-ChildItem -LiteralPath $Dir -Filter "req_*.txt" -ErrorAction SilentlyContinue) {
    if ($done.ContainsKey($req.Name)) { continue }
    Start-Sleep -Milliseconds 400
    $n = $req.BaseName.Substring(4)
    $pids = New-Object 'System.Collections.Generic.HashSet[uint32]'
    foreach ($p in Get-Process | Where-Object { $_.ProcessName -like "$ProcName*" -or $_.ProcessName -like "octave*" }) { [void]$pids.Add([uint32]$p.Id) }
    $k = 0
    foreach ($h in [WinCap]::ForPids($pids)) {
      $t = [WinCap]::Title($h)
      $kind = if ($t -match "Figure") { "fig$k" } elseif ($t -match "Octave") { "main" } else { "win$k" }
      $k++
      [void](Save-Window $h (Join-Path $Dir ("shot_{0}_{1}.png" -f $n, $kind)))
    }
    Set-Content -LiteralPath (Join-Path $Dir ("ok_{0}.txt" -f $n)) -Value "ok"
    $done[$req.Name] = $true
  }
  if (Test-Path -LiteralPath (Join-Path $Dir "stop.txt")) { break }
  Start-Sleep -Milliseconds 200
}

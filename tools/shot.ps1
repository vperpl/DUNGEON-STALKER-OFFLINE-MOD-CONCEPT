param([int]$ProcId, [string]$Out)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern int GetWindowTextW(IntPtr h, System.Text.StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint f);
  [StructLayout(LayoutKind.Sequential)] public struct R { public int L, T, Rt, B; }
}
"@
$target = [IntPtr]::Zero
$best = 0
[W]::EnumWindows({
  param($h,$l)
  $p=0; [W]::GetWindowThreadProcessId($h,[ref]$p) | Out-Null
  if ($p -eq $ProcId -and [W]::IsWindowVisible($h)) {
    $r = New-Object W+R
    if ([W]::GetWindowRect($h,[ref]$r)) {
      $a = ($r.Rt-$r.L)*($r.B-$r.T)
      if ($a -gt $script:best) { $script:best = $a; $script:target = $h }
    }
  }
  return $true
}, [IntPtr]::Zero) | Out-Null

if ($target -eq [IntPtr]::Zero) { Write-Output "NO_WINDOW"; exit 1 }
$r = New-Object W+R; [W]::GetWindowRect($target,[ref]$r) | Out-Null
$w = $r.Rt - $r.L; $h = $r.B - $r.T
Write-Output "hwnd=$target rect=$($r.L),$($r.T) ${w}x${h}"
$bmp = New-Object System.Drawing.Bitmap($w, $h)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
[W]::PrintWindow($target, $hdc, 2) | Out-Null
$g.ReleaseHdc($hdc)
$g.Dispose()
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "SAVED $((Get-Item $Out).Length)"

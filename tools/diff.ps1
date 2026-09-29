param([string]$A, [string]$B)
Add-Type -AssemblyName System.Drawing
$ia = [System.Drawing.Image]::FromFile($A)
$ib = [System.Drawing.Image]::FromFile($B)
$w = [Math]::Min($ia.Width, $ib.Width); $h = [Math]::Min($ia.Height, $ib.Height)
$ba = New-Object System.Drawing.Bitmap($ia, $w, $h)
$bb = New-Object System.Drawing.Bitmap($ib, $w, $h)
$ia.Dispose(); $ib.Dispose()
$r = [System.Drawing.Rectangle]::new(0,0,$w,$h)
$m = [System.Drawing.Imaging.ImageLockMode]::ReadOnly
$f = [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
$d1 = $ba.LockBits($r, $m, $f)
$d2 = $bb.LockBits($r, $m, $f)
$n1 = [Math]::Abs($d1.Stride) * $h
$sa = New-Object byte[] $n1; $sb = New-Object byte[] $n1
[System.Runtime.InteropServices.Marshal]::Copy($d1.Scan0, $sa, 0, $n1)
[System.Runtime.InteropServices.Marshal]::Copy($d2.Scan0, $sb, 0, $n1)
$ba.UnlockBits($d1); $bb.UnlockBits($d2)
$ba.Dispose(); $bb.Dispose()
$diff = 0; $sum = 0
for ($i = 0; $i -lt $n1; $i += 4) {
  $dr = [Math]::Abs($sa[$i] - $sb[$i]); $dg = [Math]::Abs($sa[$i+1] - $sb[$i+1]); $db = [Math]::Abs($sa[$i+2] - $sb[$i+2])
  $mx = [Math]::Max([Math]::Max($dr,$dg), $db)
  if ($mx -gt 8) { $diff++ }
  $sum += $mx
}
$px = [int]($n1 / 4)
"{0} x {1}  changed={2} ({3:N2}%)  avgmaxdiff={4:N2}" -f $w, $h, $diff, (100.0*$diff/$px), ($sum/$px)

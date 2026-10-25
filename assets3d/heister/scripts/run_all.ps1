param([string]$From = "s3_parts")
$b = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$H = "C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
$steps = @("s3_parts", "s4_extras", "s5a_uv", "s5hi", "s5b_bake", "s5c_paint", "s5d_material", "s6_anim", "s7_lod", "s8_export")
$go = $false
foreach ($s in $steps) {
    if ($s -eq $From) { $go = $true }
    if (-not $go) { continue }
    Write-Output "=== $s"
    $out = & $b -b -P "$H\scripts\$s.py" 2>&1 | Out-String
    $out -split "`n" | Where-Object { $_ -match "Error|Traceback|tris|LOD |baked|exported|saved|TOTAL|islands|coverage" } | Select-Object -First 40
    if ($out -match "Traceback") { Write-Output "FAILED at $s"; break }
}

$b = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
Set-Location C:\Users\Shaik\Downloads\heistbox\assets3d\tina\scripts
foreach ($s in 's5_assemble', 's6_anim', 's7_export') {
    $a = @(); if ($s -eq 's6_anim') { $a = @('--', '--noshots') }
    & $b -b -P "$s.py" @a 2>&1 | Select-String -NotMatch "INFO" | Out-File "_$s.log" -Encoding utf8
    "== $s"; Get-Content "_$s.log" | Select-String "Error|Traceback|LOD |EYE|export" | Select-Object -First 12
}

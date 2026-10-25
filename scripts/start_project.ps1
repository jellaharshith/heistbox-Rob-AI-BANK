$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
$nodePath = (Get-Command node.exe).Source
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Missing .venv/Scripts/python.exe. Install the backend dependencies first.'
}

function Start-ServiceProcess($port, $name, $executable, $arguments, $directory) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    if ($listener) {
        Write-Host "$name is already listening on port $port"
        return
    }
    $process = Start-Process -FilePath $executable -ArgumentList $arguments -WorkingDirectory $directory `
        -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot "$name.run.stdout.log") `
        -RedirectStandardError (Join-Path $projectRoot "$name.run.stderr.log") -PassThru
    Write-Host "Started $name (PID $($process.Id)) on port $port"
}

Start-ServiceProcess 8000 'server' $pythonPath 'main.py' $projectRoot
Start-ServiceProcess 3000 'dashboard' $nodePath 'node_modules/next/dist/bin/next dev -p 3000' (Join-Path $projectRoot 'web')
Write-Host 'Dashboard: http://localhost:3000'
Write-Host 'Backend docs: http://localhost:8000/docs'
& (Join-Path $PSScriptRoot 'start_poster_share.ps1')

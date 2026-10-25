$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root '.venv\Scripts\python.exe'
$server = Start-Process -FilePath $py -ArgumentList '-m','uvicorn','server.app:app','--host','127.0.0.1','--port','8788' -WorkingDirectory $root -PassThru
$web = Start-Process -FilePath 'npm.cmd' -ArgumentList '--prefix','web','run','dev' -WorkingDirectory $root -PassThru
try { Wait-Process -Id $server.Id,$web.Id }
finally { foreach ($p in @($server,$web)) { if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force } } }

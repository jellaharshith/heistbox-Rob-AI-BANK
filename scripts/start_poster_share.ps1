$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$shareFile = Join-Path $projectRoot 'shared/poster_share.json'
if (Test-Path -LiteralPath $shareFile) {
    $existingShare = Get-Content -LiteralPath $shareFile -Raw | ConvertFrom-Json
    if ($existingShare.pid -and (Get-Process -Id $existingShare.pid -ErrorAction SilentlyContinue)) {
        Write-Host 'Poster sharing is running.'
        return
    }
}
$toolsDir = Join-Path $env:TEMP 'heistbox-tools'
New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null
$tunnelExe = Join-Path $toolsDir 'cloudflared.exe'
if (-not (Test-Path -LiteralPath $tunnelExe)) {
    Invoke-WebRequest 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile $tunnelExe
}
$stderrLog = Join-Path $projectRoot 'poster-tunnel.stderr.log'
if (Test-Path -LiteralPath $stderrLog) { Remove-Item -LiteralPath $stderrLog -Force -ErrorAction SilentlyContinue }
$tunnelProcess = Start-Process -FilePath $tunnelExe -ArgumentList 'tunnel --url http://127.0.0.1:3000 --no-autoupdate' `
    -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $projectRoot 'poster-tunnel.stdout.log') -RedirectStandardError $stderrLog
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    Start-Sleep -Milliseconds 300
    if (Test-Path -LiteralPath $stderrLog) {
        $content = Get-Content -LiteralPath $stderrLog -Raw -ErrorAction SilentlyContinue
        if ($content) {
            $match = [regex]::Match($content, 'https://[a-z0-9-]+\.trycloudflare\.com')
            if ($match.Success) {
                @{ origin = $match.Value; pid = $tunnelProcess.Id } | ConvertTo-Json | Set-Content -LiteralPath $shareFile -Encoding utf8
                Write-Host 'Phone-accessible poster sharing is ready.'
                return
            }
        }
    }
}
throw 'Poster tunnel is still starting. Check poster-tunnel.stderr.log.'

$ErrorActionPreference = 'Stop'
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = 'C:\Users\kjyss\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$Cloudflared = Join-Path $Project 'tools\cloudflared.exe'
$Log = Join-Path $Project 'tunnel.log'
$UrlFile = Join-Path $Project 'public-url.txt'

if (-not (Test-Path $Cloudflared)) {
    throw 'tools\cloudflared.exe가 없습니다.'
}

try {
    Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 2 | Out-Null
} catch {
    Start-Process -FilePath $Python -ArgumentList 'server.py' -WorkingDirectory $Project -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

if (Test-Path $Log) { Remove-Item -LiteralPath $Log -Force }
Start-Process -FilePath $Cloudflared -ArgumentList @('tunnel','--url','http://127.0.0.1:8765','--no-autoupdate','--loglevel','info','--logfile',$Log) -WorkingDirectory $Project -WindowStyle Hidden

$PublicUrl = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $Log) {
        $Match = Select-String -Path $Log -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | Select-Object -First 1
        if ($Match) {
            $PublicUrl = $Match.Matches[0].Value
            break
        }
    }
}

if (-not $PublicUrl) { throw '공개 URL 생성 시간이 초과되었습니다.' }
Set-Content -LiteralPath $UrlFile -Value $PublicUrl -Encoding UTF8
Write-Host "공개 URL: $PublicUrl" -ForegroundColor Green
Write-Host 'PC와 터널 프로세스가 켜져 있는 동안 외부에서 접속할 수 있습니다.'

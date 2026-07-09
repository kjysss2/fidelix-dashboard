param(
  [Parameter(Mandatory=$true)]
  [string]$HostName,

  [string]$User = "root",
  [string]$KeyPath = "",
  [string]$RemoteDir = "/opt/fidelix-dashboard",
  [switch]$IncludeEnv
)

$ErrorActionPreference = "Stop"

function Require-Command($Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name 명령을 찾지 못했습니다. Windows 선택적 기능에서 OpenSSH Client를 켜주세요."
  }
}

Require-Command "ssh"
Require-Command "scp"
Require-Command "tar"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Remote = "$User@$HostName"
$SshArgs = @()
if ($KeyPath -ne "") {
  $SshArgs += @("-i", $KeyPath)
}

$Archive = Join-Path $env:TEMP "fidelix-dashboard.tar.gz"
if (Test-Path $Archive) {
  Remove-Item -LiteralPath $Archive -Force
}

Write-Host "배포 파일을 묶습니다."
$ArchiveItems = @("server.py", "refresh_once.py", "README.md", ".env.example", "static", "data/seed.json", "deploy")
if ($IncludeEnv) {
  if (Test-Path (Join-Path $ProjectRoot ".env")) {
    $ArchiveItems += ".env"
    Write-Host ".env도 함께 업로드합니다. API 키가 포함될 수 있으니 서버 접근 권한을 확인하세요."
  } else {
    Write-Host ".env 파일이 없어 .env.example만 업로드합니다."
  }
}

Push-Location $ProjectRoot
try {
  tar -czf $Archive @ArchiveItems
} finally {
  Pop-Location
}

Write-Host "원격 서버로 업로드합니다."
scp @SshArgs $Archive "${Remote}:/tmp/fidelix-dashboard.tar.gz"

Write-Host "서버에 배치하고 자동 실행을 설정합니다."
ssh @SshArgs $Remote "sudo mkdir -p $RemoteDir; sudo tar -xzf /tmp/fidelix-dashboard.tar.gz -C $RemoteDir; sudo bash $RemoteDir/deploy/naver-cloud/bootstrap-ubuntu.sh"

Write-Host ""
Write-Host "완료되었습니다. 브라우저에서 열어보세요:"
Write-Host "http://$HostName/"

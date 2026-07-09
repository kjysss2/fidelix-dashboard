$ErrorActionPreference = 'Stop'
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = 'C:\Users\kjyss\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'

$EnvFile = Join-Path $Project '.env'
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
            [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
        }
    }
}

& $Python (Join-Path $Project 'server.py')

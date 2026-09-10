# Run this script in PowerShell. Both services bind only to loopback.
param([switch]$EnableAI)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv/Scripts/python.exe'
$taskWeb = Join-Path $taskRoot 'web'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run the setup steps in README.md first.' }
if (-not (Test-Path -LiteralPath (Join-Path $taskWeb 'node_modules'))) { throw 'Run npm ci inside web first.' }
$taskPorts = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in @(3000,8000) })
if ($taskPorts.Count -gt 0) { throw 'Port 3000 or 8000 is already in use. Do not stop unrelated services; check the existing local preview first.' }
$previousAISetting = $env:MINDFUL_ENABLE_AI
$env:MINDFUL_ENABLE_AI = if ($EnableAI) { '1' } else { '0' }
$taskBackend = $null
try {
    $taskBackend = Start-Process -FilePath $taskPython -ArgumentList @('-m','uvicorn','backend.app:create_app','--factory','--host','127.0.0.1','--port','8000','--no-access-log') -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru
    $taskDeadline = (Get-Date).AddSeconds(90)
    $taskBackendReady = $false
    while ((Get-Date) -lt $taskDeadline) {
        if ($taskBackend.HasExited) { throw 'Backend startup failed. Check the AI evaluation report and installed dependencies.' }
        try {
            $taskHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2
            if ($EnableAI -and -not $taskHealth.chat_enabled) { throw 'AI was requested but is not ready.' }
            $taskBackendReady = $true
            break
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $taskBackendReady) { throw 'Backend did not become ready within 90 seconds.' }
    Write-Host 'Mindful local preparation: http://localhost:3000'
    if ($EnableAI) { Write-Host 'Loading the evaluated local adapter. Startup fails if its checks are missing.' }
    else { Write-Host 'AI disabled. Use -EnableAI only after successful training and evaluation.' }
    Write-Host 'Press Ctrl+C to stop this local development session.'
    Push-Location $taskWeb
    try { & npm.cmd run dev } finally { Pop-Location }
} finally {
    $env:MINDFUL_ENABLE_AI = $previousAISetting
    if ($taskBackend -and -not $taskBackend.HasExited) { Stop-Process -Id $taskBackend.Id -ErrorAction SilentlyContinue }
}

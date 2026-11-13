# Instala o WhatsApp MCP, mostra o QR code e deixa a ponte ligada 24/7.
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$env:Path = 'C:\msys64\ucrt64\bin;' + [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
$env:CGO_ENABLED = '1'

Write-Host "`n[1/4] Compilando a ponte do WhatsApp..." -ForegroundColor Cyan
Get-Process whatsapp-bridge -ErrorAction SilentlyContinue | Stop-Process -Force
Set-Location (Join-Path $root 'whatsapp-bridge')
go build -o whatsapp-bridge.exe .
if ($LASTEXITCODE -ne 0) { throw "Falha ao compilar a ponte" }

Write-Host "`n[2/4] Instalando o servidor MCP (Python)..." -ForegroundColor Cyan
Set-Location (Join-Path $root 'whatsapp-mcp-server')
uv sync
if ($LASTEXITCODE -ne 0) { throw "Falha no uv sync" }

$bridgeDir = Join-Path $root 'whatsapp-bridge'
if (-not (Test-Path (Join-Path $bridgeDir 'store\whatsapp.db'))) {
    Write-Host "`n[3/4] ESCANEIE O QR CODE: WhatsApp > Aparelhos conectados > Conectar aparelho" -ForegroundColor Yellow
    Write-Host "O QR abre numa janela nova. Depois que aparecer 'Connected to WhatsApp', FECHE aquela janela (no X).`n" -ForegroundColor Yellow
    Start-Process -FilePath (Join-Path $bridgeDir 'whatsapp-bridge.exe') -WorkingDirectory $bridgeDir -Wait
    if (-not (Test-Path (Join-Path $bridgeDir 'store\whatsapp.db'))) { throw "Pareamento não concluído; rode de novo." }
} else {
    Write-Host "`n[3/4] Sessão já existe, sem QR code." -ForegroundColor Green
}

Write-Host "`n[4/4] Deixando a ponte ligada sempre (inicia com o Windows e religa se cair)..." -ForegroundColor Cyan
$keeper = Join-Path $root 'manter-bridge.ps1'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$keeper`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'WhatsApp-Bridge' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName 'WhatsApp-Bridge'

Write-Host "`nPRONTO. A ponte está rodando escondida. Pode fechar esta janela." -ForegroundColor Green
Read-Host "Aperte Enter para fechar"

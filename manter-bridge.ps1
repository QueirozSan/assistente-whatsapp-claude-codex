# Mantém a ponte do WhatsApp sempre ligada (roda escondido, iniciado pela tarefa agendada).
# Se a ponte fechar ou cair, espera 15 s e liga de novo. A sessão fica salva em whatsapp-bridge\store.
$dir = Join-Path $PSScriptRoot 'whatsapp-bridge'
$exe = Join-Path $dir 'whatsapp-bridge.exe'
$log = Join-Path $PSScriptRoot 'bridge.log'

# Só uma cópia ao mesmo tempo
$m = New-Object System.Threading.Mutex($false, 'Global\WhatsAppBridgeKeeper')
if (-not $m.WaitOne(0)) { exit 0 }

while ($true) {
    if ((Test-Path $log) -and (Get-Item $log).Length -gt 5MB) { Move-Item $log "$log.old" -Force }
    # Fecha cópia solta (ex.: janela do QR) para não haver duas sessões disputando a porta 8080
    Get-Process whatsapp-bridge -ErrorAction SilentlyContinue | Stop-Process -Force
    Add-Content $log "$(Get-Date -Format s) iniciando ponte"
    $p = Start-Process -FilePath $exe -WorkingDirectory $dir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput "$log.out" -RedirectStandardError "$log.err"
    $p.WaitForExit()
    Get-Content "$log.out", "$log.err" -Tail 30 -ErrorAction SilentlyContinue | Add-Content $log
    Add-Content $log "$(Get-Date -Format s) ponte saiu (codigo $($p.ExitCode)); religando em 15 s"
    Start-Sleep -Seconds 15
}

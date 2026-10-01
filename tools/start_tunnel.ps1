<#
.SYNOPSIS
  Start Twin Lab locally and expose it through a Cloudflare quick tunnel, for testing the Google
  Form webhook.

.DESCRIPTION
  Apps Script runs on Google's servers and cannot reach localhost, so the Form needs a public
  HTTPS URL. This starts uvicorn on 127.0.0.1:7860 and a quick tunnel in front of it, then prints
  the ENDPOINT to paste into apps_script/intake.gs.

  WHAT THIS EXPOSES: while it runs, anyone with the URL can reach your local Twin Lab — the UI and
  the whole JSON API, not only the intake route. The URL is random and unlisted, but it is public.
  Close the window when you are done testing; the URL dies with it and a new one is issued next
  time.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\start_tunnel.ps1
#>
[CmdletBinding()]
param(
    [int]$Port = 7860
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$cloudflared = 'C:\Program Files (x86)\cloudflared\cloudflared.exe'
if (-not (Test-Path $cloudflared)) {
    $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cmd) { $cloudflared = $cmd.Source }
    else { throw "cloudflared not found. Install it with: winget install --id Cloudflare.cloudflared" }
}

# --- preflight -------------------------------------------------------------------

if (-not (Test-Path '.env')) {
    Write-Warning @'
No .env file. Intake will return 503 until INTAKE_HMAC_SECRET is set.

Generate one and put it in .env, and in the Apps Script project property of the same name:
    python -c "import secrets; print(secrets.token_hex(32))"
'@
} else {
    $envText = Get-Content .env -Raw
    if ($envText -notmatch '(?m)^INTAKE_HMAC_SECRET=\S') {
        Write-Warning 'INTAKE_HMAC_SECRET is empty in .env. Intake will return 503.'
    }
    if ($envText -notmatch '(?m)^SUPABASE_URL=\S') {
        Write-Host 'Note: no Supabase configured. Running on the in-memory backend -' -ForegroundColor Yellow
        Write-Host '      twins will not survive a restart. Fine for testing the Form wiring.' -ForegroundColor Yellow
    }
}

# --- the server ------------------------------------------------------------------

Write-Host "Starting uvicorn on 127.0.0.1:$Port ..." -ForegroundColor Cyan
$server = Start-Process -FilePath 'python' `
    -ArgumentList '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', "$Port" `
    -PassThru -NoNewWindow

try {
    # Wait for /api/health rather than sleeping a fixed amount.
    $ready = $false
    foreach ($attempt in 1..30) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 2
            if ($health.status -eq 'ok') { $ready = $true; break }
        } catch { }
    }
    if (-not $ready) { throw "the server did not answer /api/health on port $Port" }
    Write-Host 'Server is up.' -ForegroundColor Green

    # --- the tunnel --------------------------------------------------------------

    Write-Host ''
    Write-Host 'Opening a Cloudflare quick tunnel. This URL is PUBLIC while it runs.' -ForegroundColor Yellow
    Write-Host 'Watch for the https://<something>.trycloudflare.com line below, then set' -ForegroundColor Yellow
    Write-Host '  ENDPOINT = ''https://<that-host>/api/survey/intake''' -ForegroundColor Yellow
    Write-Host 'at the top of apps_script/intake.gs.' -ForegroundColor Yellow
    Write-Host ''
    Write-Host 'Press Ctrl+C to stop the tunnel and the server.' -ForegroundColor Cyan
    Write-Host ''

    & $cloudflared tunnel --url "http://127.0.0.1:$Port"
}
finally {
    if ($server -and -not $server.HasExited) {
        Write-Host ''
        Write-Host 'Stopping the server ...' -ForegroundColor Cyan
        Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host 'Tunnel closed. The public URL no longer resolves.' -ForegroundColor Green
}

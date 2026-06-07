$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$Python = $env:PYTHON_EXE
if ([string]::IsNullOrWhiteSpace($Python)) {
    $Python = "python"
}

Write-Host "Using Python: $Python"

if (!(Test-Path ".\.venv")) {
    & $Python -m venv .venv
}

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $VenvPython)) {
    $VenvPython = Join-Path $Root ".venv\bin\python.exe"
}
if (!(Test-Path $VenvPython)) {
    throw "Could not find Python inside .venv. Set PYTHON_EXE to a Windows Python with venv and pip."
}

& $VenvPython -m pip install -r requirements.txt

# ---- API keys ----
if ([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) {
    $env:DEEPSEEK_API_KEY = [Environment]::GetEnvironmentVariable("DEEPSEEK_API_KEY", "User")
}
if ([string]::IsNullOrWhiteSpace($env:GATEWAY_AUTH_TOKEN)) {
    $env:GATEWAY_AUTH_TOKEN = [Environment]::GetEnvironmentVariable("GATEWAY_AUTH_TOKEN", "User")
}
if ([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) {
    Write-Host "DEEPSEEK_API_KEY is not set. Set it in the environment before starting the proxy." -ForegroundColor Red
    exit 1
}

# ---- Auto-detect model_provider from Codex config ----
if ([string]::IsNullOrWhiteSpace($env:GATEWAY_MODEL_PROVIDER)) {
    $env:GATEWAY_MODEL_PROVIDER = [Environment]::GetEnvironmentVariable("GATEWAY_MODEL_PROVIDER", "User")
}
if ([string]::IsNullOrWhiteSpace($env:GATEWAY_MODEL_PROVIDER)) {
    $CodexConfig = Join-Path $env:USERPROFILE ".codex\config.toml"
    if (Test-Path $CodexConfig) {
        $matched = Select-String -Path $CodexConfig -Pattern '^model_provider\s*=\s*"(.+)"' | ForEach-Object { $_.Matches.Groups[1].Value }
        if ($matched) {
            $env:GATEWAY_MODEL_PROVIDER = $matched
            Write-Host "[auto] GATEWAY_MODEL_PROVIDER = $($env:GATEWAY_MODEL_PROVIDER)" -ForegroundColor DarkCyan
        }
    }
} else {
    Write-Host "GATEWAY_MODEL_PROVIDER = $($env:GATEWAY_MODEL_PROVIDER)" -ForegroundColor DarkCyan
}

$ProxyHost = if ($env:PROXY_HOST) { $env:PROXY_HOST } else { "127.0.0.1" }
$ProxyPort = if ($env:PROXY_PORT) { $env:PROXY_PORT } else { "3688" }

& $VenvPython -m uvicorn server:app --host $ProxyHost --port $ProxyPort

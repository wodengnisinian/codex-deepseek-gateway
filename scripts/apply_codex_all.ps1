$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$CodexDir = "$env:USERPROFILE\.codex"

Write-Host "=== Codex DeepSeek Gateway ? Apply Config ===" -ForegroundColor Cyan
Write-Host "Source : $Root"
Write-Host "Target : $CodexDir"
Write-Host ""

# ---- 1. config.toml ----
$Src = Join-Path $Root "codex\config.toml"
$Dst = Join-Path $CodexDir "config.toml"
if (Test-Path $Src) {
    if (Test-Path $Dst) {
        $Backup = "$Dst.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Copy-Item $Dst $Backup -Force
        Write-Host "[OK] backup -> $Backup" -ForegroundColor Yellow
    }
    Copy-Item $Src $Dst -Force
    Write-Host "[OK] config.toml" -ForegroundColor Green
} else {
    Write-Host "[SKIP] codex\config.toml not found (gitignored? copy from .example)" -ForegroundColor Gray
}

# ---- 2. model_catalog.json ----
$Src = Join-Path $Root "codex\model_catalog.json"
$Dst = Join-Path $CodexDir "model_catalog.json"
if (Test-Path $Src) {
    if (Test-Path $Dst) {
        $Backup = "$Dst.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Copy-Item $Dst $Backup -Force
    }
    Copy-Item $Src $Dst -Force
    Write-Host "[OK] model_catalog.json" -ForegroundColor Green
} else {
    Write-Host "[SKIP] model_catalog.json not found" -ForegroundColor Gray
}

# ---- 3. skills (merge ? do not wipe system skills) ----
$Src = Join-Path $Root "codex\skills"
$Dst = Join-Path $CodexDir "skills"
if (Test-Path $Src) {
    if (!(Test-Path $Dst)) {
        New-Item -ItemType Directory -Path $Dst -Force | Out-Null
    }
    # Copy skill dirs individually so we don't delete untracked skills
    Get-ChildItem -Directory -Path $Src | ForEach-Object {
        $TargetDir = Join-Path $Dst $_.Name
        Copy-Item $_.FullName $TargetDir -Recurse -Force
        Write-Host "  [skill] $($_.Name)" -ForegroundColor DarkCyan
    }
    Write-Host "[OK] skills synced" -ForegroundColor Green
} else {
    Write-Host "[SKIP] codex\skills not found" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Done. Restart Codex for changes to take effect." -ForegroundColor Cyan

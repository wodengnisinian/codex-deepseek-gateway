$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$CodexDir = "$env:USERPROFILE\.codex"

# 检查配置文件
$ConfigSrc = Join-Path $Root "codex\config.toml"
$ConfigDst = Join-Path $CodexDir "config.toml"

if (!(Test-Path $ConfigSrc)) {
    Write-Host "config.toml not found at $ConfigSrc" -ForegroundColor Red
    exit 1
}

# 备份现有配置
if (Test-Path $ConfigDst) {
    $Backup = "$ConfigDst.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $ConfigDst $Backup
    Write-Host "Backed up existing config to $Backup" -ForegroundColor Yellow
}

# 同步配置文件
Copy-Item $ConfigSrc $ConfigDst -Force
Write-Host "Config synced: $ConfigSrc → $ConfigDst" -ForegroundColor Green

Write-Host "Done. Restart Codex to apply changes." -ForegroundColor Cyan

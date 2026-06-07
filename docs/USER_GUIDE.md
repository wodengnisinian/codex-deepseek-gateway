# User Guide

## Starting the Gateway

### EXE Launcher

1. Double-click CDG Launcher.exe
2. Enter your DeepSeek API Key
3. Select a model from the dropdown
4. Click Start Gateway

The gateway runs at http://127.0.0.1:3688

### PowerShell Script

`powershell
.\scripts\run_proxy.ps1
`

## Configuring Codex Desktop

### Mode 1: Direct API Key (Recommended)

1. Copy codex/config.toml.example to %USERPROFILE%\.codex\config.toml
2. Uncomment the Mode 1 section
3. Run: .\scripts\apply_codex_all.ps1
4. Restart Codex

### Mode 2: Plugin-Compatible

Use this mode if you need to stay logged into OpenAI within Codex:

`powershell
[Environment]::SetEnvironmentVariable("GATEWAY_AUTH_TOKEN", "local-gateway-token", "User")
[Environment]::SetEnvironmentVariable("GATEWAY_MODEL_PROVIDER", "deepseek_gateway_plugin_mode", "User")
`

Then uncomment Mode 2 in config.toml and run apply_codex_all.ps1.

## Model Selection

Available models are listed in codex/model_catalog.json. The gateway exposes them at /v1/models.

## Stopping the Gateway

- EXE: Click Stop Gateway or close the window
- Script: Press Ctrl+C

## Environment Variables

| Variable | Required | Default |
|----------|----------|---------|
| DEEPSEEK_API_KEY | Yes | - |
| DEEPSEEK_BASE_URL | No | https://api.deepseek.com |
| DEFAULT_MODEL | No | deepseek-v4-flash |
| PROXY_PORT | No | 3688 |
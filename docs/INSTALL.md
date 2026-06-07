# Installation Guide

## Prerequisites

- Windows 10/11 64-bit
- DeepSeek API Key (get one at https://platform.deepseek.com)

## Option 1: Download Pre-built EXE (Recommended)

1. Go to [Releases](https://github.com/wodengnisinian/codex-deepseek-gateway/releases)
2. Download CDG Launcher.exe
3. Double-click to run
4. Enter your DeepSeek API Key in the launcher
5. Click Start Gateway

## Option 2: Run from Source

`powershell
git clone https://github.com/wodengnisinian/codex-deepseek-gateway.git
cd codex-deepseek-gateway

# Set API Key
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "sk-your-key", "User")

# Run gateway
.\scripts\run_proxy.ps1
`

## Option 3: Build from Source

See [BUILD.md](BUILD.md) for PyInstaller build instructions.

## Verify Installation

`powershell
curl http://127.0.0.1:3688/health
`

Expected response: {"status":"ok"}
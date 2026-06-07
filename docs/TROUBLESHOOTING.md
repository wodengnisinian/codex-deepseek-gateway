# Troubleshooting

## Gateway Won't Start

**Symptom**: Port 3688 already in use

**Fix**:
`powershell
netstat -ano | findstr :3688
taskkill /PID <PID> /F
`

## 401 Unauthorized

**Symptom**: curl http://127.0.0.1:3688/v1/models returns 401

**Fix**: Set DEEPSEEK_API_KEY environment variable and restart terminal.

## Model Not Found

**Symptom**: 404 when using a model

**Fix**: Check available models at http://127.0.0.1:3688/v1/models or update codex/model_catalog.json.

## Connection Refused

**Symptom**: curl fails with connection refused

**Fix**: Ensure the gateway is running. Check for firewall blocking port 3688.

## EXE Won't Launch

**Symptom**: Double-click does nothing

**Fix**: 
- Right-click > Run as Administrator
- Check Windows Defender quarantine
- Re-download from GitHub Releases

## DeepSeek API Errors

**Symptom**: 502 Bad Gateway from DeepSeek

**Fix**: Check your DeepSeek API quota at https://platform.deepseek.com

## Codex Not Using Gateway

**Symptom**: Codex still uses OpenAI models

**Fix**: Verify config.toml is synced (%USERPROFILE%\.codex\config.toml) and restart Codex.
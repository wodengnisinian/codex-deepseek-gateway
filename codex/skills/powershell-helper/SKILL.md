# PowerShell / Windows 操作规则

## 通用规则
- 所有脚本使用 PowerShell，不要使用 Bash
- 路径分隔符使用反斜杠 `\` 或 PowerShell 兼容的 `Join-Path`
- 换行符使用 CRLF（Windows 默认）

## 环境变量
- 通过 `$env:VAR_NAME` 读取环境变量
- 用户级环境变量通过 `[Environment]::GetEnvironmentVariable("VAR_NAME", "User")` 读取

## 脚本规范
- 脚本开头设置 `$ErrorActionPreference = "Stop"`
- 路径使用 `Resolve-Path` 和 `Join-Path` 确保兼容性
- Python 虚拟环境路径为 `.venv\Scripts\python.exe`（Windows）

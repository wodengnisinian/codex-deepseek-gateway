# Changelog


## [v1.0.1] - 2026-06-24

### Fixed
- **Windows no-console**: Eliminated all powershell.exe / cmd.exe popup windows
  - Replaced subprocess.run(powershell) with winreg for API key management
  - Replaced powershell-based port-kill with ctypes GetExtendedTcpTable + TerminateProcess
  - Removed QProcess, LogReader, _gw_proc, find_run_script() legacy code
  - Gateway now starts via embedded uvicorn.Server in a QThread (no external process)
- **Anti-duplicate-start guards**: Added _is_starting, _last_start_time, _start_debounce_sec
- **Port occupation check**: Socket-based _is_port_listening() before gateway start
- **Health-check QTimer**: Only refreshes UI status; does not auto-restart gateway
- **PyInstaller**: Enforced --noconsole --windowed and console=False in spec

[v1.0.1]: https://github.com/wodengnisinian/codex-deepseek-gateway/releases/tag/v1.0.1

All notable changes to this project will be documented in this file.

## [v1.0.0] - 2025-06-07

### Added
- PySide6 desktop launcher with system tray support
- Windows single-file executable (CDG Launcher.exe)
- Built-in uvicorn gateway server
- Responses API to DeepSeek Chat Completions protocol conversion
- Codex plugin tool protocol adaptation (namespace, tool_search, custom tools)
- Tool protocol hint injection for DeepSeek cache optimization
- Model catalog with dynamic /v1/models endpoint
- Health check endpoint
- Plugin-compatible mode with local auth token
- Streaming and non-streaming response support
- Codex config.toml template with two integration modes

[v1.0.0]: https://github.com/wodengnisinian/codex-deepseek-gateway/releases/tag/v1.0.0
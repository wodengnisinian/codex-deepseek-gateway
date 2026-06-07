# Changelog

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
# DeepSeek Gateway — Codex 本地网关规则

## 模型映射
- `deepseek-v4-flash` → DeepSeek V4 Flash（快速模型）
- `deepseek-v4` → DeepSeek V4（标准模型）
- `deepseek-reasoner` → DeepSeek Reasoner（推理模型）

## 网关地址
本地网关运行在 `http://127.0.0.1:3688/v1`，使用 OpenAI Responses API 兼容接口。

## 使用方式
1. 确保 `.env` 中已配置 `DEEPSEEK_API_KEY`
2. 运行 `scripts/run_proxy.ps1` 启动网关
3. Codex 会自动通过本地网关调用 DeepSeek 模型

## 注意事项
- 不要直接在 Codex 配置中写入真实 DeepSeek API Key
- 网关启动后可通过 `http://127.0.0.1:3688/health` 检查健康状态
- 所有模型请求先经过本地网关再转发到 DeepSeek API

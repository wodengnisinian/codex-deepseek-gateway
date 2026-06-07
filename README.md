# Codex DeepSeek Gateway

```
Codex Desktop  →  http://127.0.0.1:3688/v1  →  网关  →  DeepSeek API
```

本地兼容网关，将 Codex 的 Responses API 协议转换为 DeepSeek Chat Completions，让 Codex 使用 DeepSeek 模型。不修改 Codex 本身。

## 快速开始

```powershell
cd codex-deepseek-gateway

# 1. 设置 API Key（重启终端生效）
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "sk-your-key", "User")

# 2. 启动网关
.\scripts\run_proxy.ps1
```

网关启动后监听 `http://127.0.0.1:3688`。

### 插件兼容模式

如需在 Codex Desktop 中保持 OpenAI 登录态同时使用插件，额外设置两个环境变量：

```powershell
[Environment]::SetEnvironmentVariable("GATEWAY_AUTH_TOKEN", "local-gateway-token", "User")
[Environment]::SetEnvironmentVariable("GATEWAY_MODEL_PROVIDER", "deepseek_gateway_plugin_mode", "User")
```

然后将 `codex/config.toml` 中"模式二"的注释去掉，"模式一"注释掉，运行：

```powershell
.\scripts\apply_codex_all.ps1
```

重启 Codex 即可。

## 项目结构

```
server.py                   # FastAPI 网关主程序
adapters/
  chat_to_responses.py       # Chat Completions → Responses API
  responses_to_chat.py       # Responses API → Chat Completions
  tools_adapter.py           # Codex 插件工具协议适配
tests/
  test_adapters.py           # 适配器单元测试
  test_server.py             # 服务器测试
codex/
  config.toml                # 本地配置模板（gitignore，不提交）
  config.toml.example        # 配置示例（两种模式合并在一个文件）
  model_catalog.json         # 模型目录
  skills/                    # 本地技能文件
scripts/
  run_proxy.ps1              # 一键启动（自动 venv + pip）
  apply_codex_all.ps1        # 同步配置到 %USERPROFILE%\.codex
  test_*.ps1                 # 集成测试脚本
```

## 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/v1/models` | 模型列表（从 `codex/model_catalog.json` 动态读取） |
| POST | `/v1/responses` | Responses → Chat Completions 协议转换 |

## 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | 否 | DeepSeek API 地址，默认 `https://api.deepseek.com` |
| `DEFAULT_MODEL` | 否 | 默认模型，默认 `deepseek-v4-flash` |
| `PROXY_PORT` | 否 | 网关端口，默认 `3688` |
| `GATEWAY_AUTH_TOKEN` | 否 | 网关本地鉴权 token（插件兼容模式需要） |
| `GATEWAY_MODEL_PROVIDER` | 否 | 覆盖 `/v1/models` 的 `owned_by` 字段 |
| `DEEPSEEK_THINKING` | 否 | 推理开关，`enabled` / `disabled` |
| `DEEPSEEK_REASONING_EFFORT` | 否 | 推理深度，`low` / `medium` / `high` / `max` |

## 工具调用流程

```
1. Codex 发送 /v1/responses（带 tools）
2. 网关将 Responses 工具转为 Chat Completions 工具
3. DeepSeek 返回 tool_calls
4. 网关转为 Responses function_call 项返回
5. Codex 本地执行工具，发送 function_call_output
6. 网关转为 role=tool Chat 消息
7. DeepSeek 继续返回最终文本
```

## 工具协议映射

| Codex 工具类型 | DeepSeek 编码 | 解码回 |
|---------------|-------------|--------|
| `function` | 原函数名 | `function_call` |
| `namespace` | `cx_*__*` 别名 | `function_call` + namespace |
| `tool_search` | `tool_search` | `tool_search_call` |
| `custom` | `custom__*` 别名 | `custom_tool_call` |

## 缓存策略

网关仅在 Codex 发送插件工具（namespace / tool_search / custom）时才插入 tool protocol hint，并**合并到第一条 system 消息**中，避免 DeepSeek 128-token 缓存块被碎片化。

| 线程类型 | 前缀一致性 | 预期命中率 |
|---------|-----------|-----------|
| 编码线程（带工具） | 同线程 hint + instructions 不变 | 98%+ |
| 闲聊线程（无工具） | 同线程 instructions 不变 | 98%+ |
| 新线程首次请求 | 必然 miss | 0% |

剩余 ~1-2% miss（未缓存命中）来自新线程初始化和 128-token 缓存块末尾碎片，无法通过代码消除。

## 测试

```powershell
# 单元测试（不需要网络）
python -m unittest discover -s tests

# 集成测试（需要网关运行中）
.\scripts\test_health.ps1
.\scripts\test_models.ps1
.\scripts\test_response.ps1
.\scripts\test_stream_response.ps1
.\scripts\test_tool_call.ps1
.\scripts\test_stream_tool_call.ps1
```

## 许可证

MIT

---

## 撰稿人

- [wodengnisinian](https://github.com/wodengnisinian)

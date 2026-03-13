# EmailAssistant - AI 邮件助手

用自然语言发邮件的智能助手。支持 GUI、API、MCP Server 三种使用方式。

## 功能

- **自然语言发邮件** — "帮我给 test@qq.com 发个会议通知" 一句话搞定
- **多模型意图解析** — 智谱 GLM / DeepSeek / 通义千问 / Claude / 本地规则
- **附件支持** — 自动识别文件路径并附加
- **MCP Server** — 可被 Claude Code / Claude Desktop 等 AI 工具直接调用

## 快速开始

### 方式一：Windows 本机安装

```bash
# 1. 一键安装
双击 install.bat

# 2. 编辑配置（填入 LLM API Key）
编辑 config.json

# 3. 一键启动（API + GUI）
双击 start_all.bat
```

### 方式二：Docker

```bash
# 1. 准备配置
cp config.example.json config.json
# 编辑 config.json 填入 API Key

# 2. 启动
docker-compose up -d

# 3. 如需 MCP SSE 模式
docker-compose --profile mcp-sse up -d
```

## 前置依赖

- **Python 3.10+**（Windows 安装）
- **EmailMarketer** 服务运行在 `localhost:8100`（用于实际发送邮件）

## 配置说明

编辑 `config.json`：

| 字段 | 说明 |
|------|------|
| `model` | 当前使用的模型：`zhipu` / `deepseek` / `qwen` / `claude` / `local` |
| `models.*.api_key` | 对应模型的 API Key |
| `emailmarketer.api_url` | EmailMarketer API 地址（默认 `http://localhost:8100`） |
| `emailmarketer.api_key` | EmailMarketer API Key |

> 不想配 API Key？选择 `local` 模式，使用本地规则解析（无需联网）。

## API 接口

启动：`python run_api.py`（端口 8200）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/parse` | 意图解析（`{"message": "..."}` → 结构化 JSON） |
| POST | `/api/v1/send` | 直接发邮件（`to_email`, `subject`, `body`, `attachment_path`） |
| POST | `/api/v1/chat` | 一步到位：解析 → 发邮件或聊天回复 |

## MCP Server 集成

### Claude Code

在项目根目录 `.mcp.json` 中添加：

```json
{
  "mcpServers": {
    "email-assistant": {
      "command": "python",
      "args": ["<路径>/EmailAssistant/run_mcp.py"],
      "cwd": "<路径>/EmailAssistant",
      "env": {
        "EA_API_URL": "http://localhost:8200"
      }
    }
  }
}
```

### Claude Desktop

在 `claude_desktop_config.json` 中添加相同配置。

### MCP Tools

| Tool | 说明 |
|------|------|
| `smart_email(message)` | 自然语言发邮件 |
| `parse_email_intent(message)` | 仅解析意图，不发送 |
| `send_email(to_email, subject, body, attachment_path)` | 直接发邮件 |
| `email_chat(message)` | 智能聊天 |

### SSE 模式

```bash
python run_mcp.py --transport sse --port 8201
```

## 端口分配

| 服务 | 端口 |
|------|------|
| API | 8200 |
| MCP SSE | 8201 |

## 项目结构

```
EmailAssistant/
├── main.py              # GUI 主程序
├── intent_parser.py     # 意图解析引擎
├── email_client.py      # EmailMarketer API 客户端
├── config_manager.py    # 配置管理
├── config.json          # 运行配置
├── config.example.json  # 配置模板
├── run_api.py           # FastAPI 服务
├── run_mcp.py           # MCP Server
├── requirements.txt     # Python 依赖
├── install.bat          # Windows 一键安装
├── start_all.bat        # Windows 一键启动
├── Dockerfile           # Docker 镜像
└── docker-compose.yml   # Docker 编排
```

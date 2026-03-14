"""
EmailAssistant MCP Server
传输协议: stdio (默认) / SSE (--transport sse, 端口 8201)
支持 Bearer Token 认证（SSE 模式下）
"""
import argparse
import os
import json
import secrets
import httpx
from mcp.server.fastmcp import FastMCP

# ---------- 配置 ----------

API_URL = os.environ.get("EA_API_URL", "http://localhost:8200")
SSE_HOST = os.environ.get("EA_SSE_HOST", "0.0.0.0")
SSE_PORT = int(os.environ.get("EA_SSE_PORT", "8201"))
HTTP_TIMEOUT = float(os.environ.get("EA_HTTP_TIMEOUT", "60"))

# Bearer Token 认证（SSE 模式下生效）
# 设置环境变量 EA_AUTH_TOKEN 或自动生成
AUTH_TOKEN = os.environ.get("EA_AUTH_TOKEN", "")

server = FastMCP(
    "email-assistant",
    host=SSE_HOST,
    port=SSE_PORT,
)

# ---------- HTTP 客户端 ----------

async def _post(path: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(f"{API_URL}{path}", json=data)
        resp.raise_for_status()
        return resp.json()

async def _get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(f"{API_URL}{path}")
        resp.raise_for_status()
        return resp.json()

def _json_text(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)

def _error_text(msg: str) -> str:
    return json.dumps({"error": msg}, ensure_ascii=False)

# ---------- MCP Tools ----------

@server.tool()
async def smart_email(message: str) -> str:
    """用自然语言发送邮件，一句话搞定。

示例:
- "帮我给 test@qq.com 发一封会议通知，内容是明天下午3点开会"
- "发邮件给 boss@company.com，标题是项目进度，正文写本周已完成80%"

自动解析收件人、标题、正文并发送。如果信息不完整会提示补充。
    """
    try:
        result = await _post("/api/v1/chat", {"message": message})
        return _json_text(result)
    except httpx.ConnectError:
        return _error_text("无法连接 EmailAssistant API (localhost:8200)，请确认已启动 run_api.py")
    except httpx.HTTPStatusError as e:
        return _error_text(f"API 错误 {e.response.status_code}: {e.response.text}")

@server.tool()
async def parse_email_intent(message: str) -> str:
    """解析自然语言中的邮件意图，返回结构化结果（不发送）。

返回 JSON 包含: action, to_email, subject, body, attachment 等字段。
用于预览解析结果，确认后再发送。
    """
    try:
        result = await _post("/api/v1/parse", {"message": message})
        return _json_text(result)
    except httpx.ConnectError:
        return _error_text("无法连接 EmailAssistant API (localhost:8200)")
    except httpx.HTTPStatusError as e:
        return _error_text(f"API 错误 {e.response.status_code}: {e.response.text}")

@server.tool()
async def send_email(
    to_email: str,
    subject: str,
    body: str = "",
    attachment_path: str | None = None
) -> str:
    """直接发送邮件（需提供完整参数）。

参数:
- to_email: 收件人邮箱
- subject: 邮件标题
- body: 邮件正文
- attachment_path: 附件本地路径（可选）
    """
    try:
        data = {
            "to_email": to_email,
            "subject": subject,
            "body": body,
        }
        if attachment_path:
            data["attachment_path"] = attachment_path
        result = await _post("/api/v1/send", data)
        return _json_text(result)
    except httpx.ConnectError:
        return _error_text("无法连接 EmailAssistant API (localhost:8200)")
    except httpx.HTTPStatusError as e:
        return _error_text(f"API 错误 {e.response.status_code}: {e.response.text}")

@server.tool()
async def email_chat(message: str) -> str:
    """与邮件助手聊天。可以问邮件相关问题，也可以闲聊。"""
    try:
        result = await _post("/api/v1/chat", {"message": message})
        return _json_text(result)
    except httpx.ConnectError:
        return _error_text("无法连接 EmailAssistant API (localhost:8200)")
    except httpx.HTTPStatusError as e:
        return _error_text(f"API 错误 {e.response.status_code}: {e.response.text}")

# ---------- Bearer Token 认证中间件 ----------

SERVER_CARD = {
    "name": "email-assistant",
    "description": "AI Email Assistant - Send emails with natural language via MCP",
    "tools": [
        {"name": "smart_email", "description": "Send email using natural language"},
        {"name": "parse_email_intent", "description": "Parse email intent from natural language (no send)"},
        {"name": "send_email", "description": "Send email with explicit parameters"},
        {"name": "email_chat", "description": "Chat with email assistant"},
    ],
}


class BearerAuthMiddleware:
    """ASGI 中间件：验证 Authorization: Bearer <token>"""

    # 不需要认证的路径
    PUBLIC_PATHS = {"/.well-known/mcp/server-card.json"}

    def __init__(self, app, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")

            # 公开端点：server-card.json
            if path == "/.well-known/mcp/server-card.json":
                body = json.dumps(SERVER_CARD, ensure_ascii=False).encode()
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        [b"content-type", b"application/json"],
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": body,
                })
                return

            # 需要认证的端点
            headers = dict(scope.get("headers", []))
            token_value = ""

            # 1. Authorization: Bearer xxx
            auth = headers.get(b"authorization", b"").decode()
            if auth.startswith("Bearer "):
                token_value = auth[7:]

            # 2. token 头（Smithery Connect 方式）
            if not token_value:
                token_value = headers.get(b"token", b"").decode()

            # 3. URL 查询参数 (?token=xxx 或 ?authorization=Bearer%20xxx)
            if not token_value:
                from urllib.parse import parse_qs
                qs = scope.get("query_string", b"").decode()
                params = parse_qs(qs)
                token_value = params.get("token", [""])[0]
                if not token_value:
                    auth_qs = params.get("authorization", [""])[0]
                    if auth_qs.startswith("Bearer "):
                        token_value = auth_qs[7:]

            if token_value != self.token:
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"www-authenticate", b"Bearer"],
                    ],
                })
                body = json.dumps({"error": "Invalid or missing Bearer token"}).encode()
                await send({
                    "type": "http.response.body",
                    "body": body,
                })
                return

        await self.app(scope, receive, send)

# ---------- 启动 ----------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EmailAssistant MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"])
    parser.add_argument("--port", type=int, default=SSE_PORT)
    parser.add_argument("--token", default=AUTH_TOKEN, help="Bearer Token (留空则自动生成)")
    args = parser.parse_args()

    if args.transport == "sse":
        # 确定 Token
        token = args.token or secrets.token_urlsafe(32)
        server.settings.port = args.port

        print("=" * 60)
        print("  EmailAssistant MCP Server (SSE)")
        print(f"  端口: {args.port}")
        print(f"  URL:  http://localhost:{args.port}/sse")
        print(f"  Token: {token}")
        print("=" * 60)
        print("  其他用户连接时需要在 Header 中提供:")
        print(f"  Authorization: Bearer {token}")
        print("=" * 60)

        # 获取 SSE 应用并包装认证中间件
        app = server.sse_app()
        auth_app = BearerAuthMiddleware(app, token)

        import uvicorn
        uvicorn.run(auth_app, host=SSE_HOST, port=args.port)
    else:
        server.run(transport="stdio")

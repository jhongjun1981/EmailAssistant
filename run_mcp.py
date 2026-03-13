"""
EmailAssistant MCP Server
传输协议: stdio (默认) / SSE (--transport sse, 端口 8201)
"""
import argparse
import os
import json
import httpx
from mcp.server.fastmcp import FastMCP

# ---------- 配置 ----------

API_URL = os.environ.get("EA_API_URL", "http://localhost:8200")
SSE_HOST = os.environ.get("EA_SSE_HOST", "0.0.0.0")
SSE_PORT = int(os.environ.get("EA_SSE_PORT", "8201"))
HTTP_TIMEOUT = float(os.environ.get("EA_HTTP_TIMEOUT", "60"))

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

# ---------- 启动 ----------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EmailAssistant MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"])
    parser.add_argument("--port", type=int, default=SSE_PORT)
    args = parser.parse_args()

    if args.transport == "sse":
        server.settings.port = args.port
        server.run(transport="sse")
    else:
        server.run(transport="stdio")

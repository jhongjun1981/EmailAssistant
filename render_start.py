"""
Render 云部署启动器
在一个进程中同时启动 FastAPI (内部) + MCP SSE Server (对外)
"""
import os
import sys
import threading
import time
import uvicorn

# ---------- 端口配置 ----------
# Render 通过 PORT 环境变量指定对外端口
EXTERNAL_PORT = int(os.environ.get("PORT", "10000"))
INTERNAL_API_PORT = int(os.environ.get("EA_API_PORT", "8200"))

# MCP SSE Server 使用 Render 分配的端口
os.environ["EA_SSE_PORT"] = str(EXTERNAL_PORT)
os.environ["EA_API_URL"] = f"http://127.0.0.1:{INTERNAL_API_PORT}"


def start_api_server():
    """在后台线程启动 FastAPI"""
    uvicorn.run(
        "run_api:app",
        host="127.0.0.1",
        port=INTERNAL_API_PORT,
        log_level="warning",
    )


def start_mcp_server():
    """启动 MCP SSE Server（主线程）"""
    from run_mcp import server, BearerAuthMiddleware
    from config_manager import load_config
    import secrets

    # 读取 Token
    config = load_config()
    token = os.environ.get("EA_AUTH_TOKEN", "") or config.get("mcp_auth_token", "") or secrets.token_urlsafe(32)

    print("=" * 60)
    print("  EmailAssistant MCP Server (Render)")
    print(f"  External Port: {EXTERNAL_PORT}")
    print(f"  Internal API:  127.0.0.1:{INTERNAL_API_PORT}")
    print(f"  Token: {token[:8]}...")
    print("=" * 60)

    server.settings.port = EXTERNAL_PORT
    app = server.sse_app()
    auth_app = BearerAuthMiddleware(app, token)

    uvicorn.run(auth_app, host="0.0.0.0", port=EXTERNAL_PORT, log_level="info")


if __name__ == "__main__":
    # 1. 后台启动 API
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    # 等待 API 就绪
    time.sleep(2)
    print(f"[OK] FastAPI started on 127.0.0.1:{INTERNAL_API_PORT}")

    # 2. 主线程启动 MCP SSE
    start_mcp_server()

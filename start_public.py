"""
EmailAssistant 公网发布启动器
启动 MCP SSE Server + ngrok 隧道，输出公网连接信息
"""
import os
import sys
import json
import secrets
import threading
import time
import signal

# ---------- 配置 ----------
SSE_PORT = int(os.environ.get("EA_SSE_PORT", "8201"))

# Token 优先级: 环境变量 > config.json > 随机生成
def _load_token():
    env_token = os.environ.get("EA_AUTH_TOKEN", "")
    if env_token:
        return env_token
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        token = cfg.get("mcp_auth_token", "")
        if token:
            return token
    return secrets.token_urlsafe(32)

AUTH_TOKEN = _load_token()


def start_ngrok(port: int) -> str:
    """启动 ngrok 隧道，返回公网 URL"""
    try:
        from pyngrok import ngrok, conf

        # 从 config.json 读取 ngrok authtoken
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        ngrok_token = ""
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            ngrok_token = cfg.get("ngrok_authtoken", "")

        pyngrok_conf = conf.get_default()
        if not pyngrok_conf.auth_token and ngrok_token:
            ngrok.set_auth_token(ngrok_token)
            print(f"  ngrok authtoken 已从 config.json 加载")
        elif not pyngrok_conf.auth_token:
            print("\n" + "=" * 60)
            print("  [错误] 未配置 ngrok authtoken")
            print("  请在 config.json 中添加 \"ngrok_authtoken\": \"你的token\"")
            print("=" * 60)
            sys.exit(1)

        # 启动隧道
        tunnel = ngrok.connect(port, "http")
        return tunnel.public_url
    except ImportError:
        print("[错误] pyngrok 未安装，请运行: pip install pyngrok")
        sys.exit(1)
    except Exception as e:
        print(f"[错误] ngrok 启动失败: {e}")
        sys.exit(1)


def start_mcp_sse(token: str):
    """启动 MCP SSE Server（带认证）"""
    # 导入 run_mcp 中的组件
    sys.path.insert(0, os.path.dirname(__file__))

    from run_mcp import server, BearerAuthMiddleware
    import uvicorn

    app = server.sse_app()
    auth_app = BearerAuthMiddleware(app, token)

    uvicorn.run(auth_app, host="0.0.0.0", port=SSE_PORT, log_level="warning")


def main():
    print("\n[1/2] 启动 ngrok 隧道...")
    public_url = start_ngrok(SSE_PORT)

    # SSE 端点路径
    sse_url = f"{public_url}/sse"

    print("\n" + "=" * 60)
    print("  ✅ EmailAssistant MCP Server 已上线！")
    print("=" * 60)
    print(f"  公网 URL:  {sse_url}")
    print(f"  Token:     {AUTH_TOKEN}")
    print("=" * 60)
    print("  其他用户连接方式:")
    print(f"  1. URL 填入: {sse_url}")
    print(f"  2. Token 填入: {AUTH_TOKEN}")
    print("=" * 60)
    print()

    # 保存连接信息到文件（方便分享）
    info = {
        "name": "EmailAssistant",
        "url": sse_url,
        "token": AUTH_TOKEN,
        "tools": [
            "smart_email - 自然语言发邮件",
            "parse_email_intent - 解析邮件意图",
            "send_email - 直接发送邮件",
            "email_chat - 聊天问答",
        ],
    }
    info_path = os.path.join(os.path.dirname(__file__), "public_server_info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(f"  连接信息已保存到: {info_path}")
    print("  按 Ctrl+C 停止服务\n")

    # 启动 MCP SSE Server（阻塞）
    print("[2/2] 启动 MCP SSE Server...")
    try:
        start_mcp_sse(AUTH_TOKEN)
    except KeyboardInterrupt:
        print("\n服务已停止")
        from pyngrok import ngrok
        ngrok.kill()


if __name__ == "__main__":
    main()

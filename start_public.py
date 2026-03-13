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
AUTH_TOKEN = os.environ.get("EA_AUTH_TOKEN", "") or secrets.token_urlsafe(32)


def start_ngrok(port: int) -> str:
    """启动 ngrok 隧道，返回公网 URL"""
    try:
        from pyngrok import ngrok, conf

        # 检查是否配置了 authtoken
        config = conf.get_default()
        if not config.auth_token:
            print("\n" + "=" * 60)
            print("  首次使用需要配置 ngrok authtoken")
            print("  1. 去 https://dashboard.ngrok.com/signup 注册（免费）")
            print("  2. 复制你的 authtoken")
            print("=" * 60)
            token = input("  请粘贴你的 ngrok authtoken: ").strip()
            if not token:
                print("  [错误] authtoken 不能为空")
                sys.exit(1)
            ngrok.set_auth_token(token)
            print("  authtoken 已保存！\n")

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

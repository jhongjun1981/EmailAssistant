"""
EmailAssistant FastAPI 服务
端口: 8200
"""
import argparse
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from config_manager import load_config
from intent_parser import parse_intent, chat_with_llm
from email_client import EmailClient

app = FastAPI(title="EmailAssistant API", version="1.0.0")

# ---------- 请求模型 ----------

class MessageRequest(BaseModel):
    message: str

class SendRequest(BaseModel):
    to_email: str
    subject: str
    body: str = ""
    attachment_path: str | None = None

# ---------- 全局配置 ----------

_config = None
_email_client = None

def _get_config():
    global _config
    if _config is None:
        _config = load_config()
    return _config

def _get_email_client():
    global _email_client
    if _email_client is None:
        _email_client = EmailClient(_get_config())
    return _email_client

# ---------- 接口 ----------

@app.get("/api/v1/health")
def health():
    """健康检查"""
    client = _get_email_client()
    em_ok = client.check_health()
    return {
        "status": "ok",
        "emailmarketer_connected": em_ok
    }

@app.post("/api/v1/parse")
def parse(req: MessageRequest):
    """意图解析：自然语言 → 结构化 JSON"""
    config = _get_config()
    result = parse_intent(req.message, config)
    return result

@app.post("/api/v1/send")
def send(req: SendRequest):
    """直接发邮件"""
    client = _get_email_client()
    result = client.send_email(
        to_email=req.to_email,
        subject=req.subject,
        body=req.body,
        attachment_path=req.attachment_path
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message", "发送失败"))
    return result

@app.post("/api/v1/chat")
def chat(req: MessageRequest):
    """一步到位：解析意图 → 发邮件或聊天回复"""
    config = _get_config()
    result = parse_intent(req.message, config)
    action = result.get("action")

    if action == "send":
        # 检查必填字段
        to_email = result.get("to_email")
        if not to_email:
            return {
                "action": "need_info",
                "message": "缺少收件人邮箱，请补充",
                "parsed": result
            }
        # 发送邮件
        client = _get_email_client()
        send_result = client.send_email(
            to_email=to_email,
            subject=result.get("subject", ""),
            body=result.get("body", ""),
            attachment_path=result.get("attachment")
        )
        return {
            "action": "sent",
            "send_result": send_result,
            "parsed": result
        }
    elif action == "chat":
        return {
            "action": "chat",
            "reply": result.get("reply", "")
        }
    else:
        # LLM 聊天兜底
        reply = chat_with_llm(req.message, config)
        return {
            "action": "chat",
            "reply": reply
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8200)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run(
        "run_api:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

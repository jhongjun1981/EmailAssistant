"""
内置邮件发送模块 — 支持 SMTP 和 Resend API 两种方式
- 本地：走 SMTP（QQ邮箱等）
- 云端（Render等）：走 Resend API（HTTPS，不受端口限制）
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


# ---------- Resend API 发送 ----------

def _send_via_resend(
    api_key: str,
    from_email: str,
    to_email: str,
    subject: str,
    body: str = "",
) -> dict:
    """通过 Resend API 发送邮件（HTTPS，不受 SMTP 端口限制）"""
    try:
        import resend
        resend.api_key = api_key

        params = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "text": body or "",
        }
        result = resend.Emails.send(params)
        return {"success": True, "message": f"邮件发送成功（Resend）！→ {to_email}，ID: {result.get('id', 'N/A')}"}
    except Exception as e:
        return {"success": False, "message": f"Resend 发送失败: {str(e)}"}


# ---------- 常见邮箱的 SMTP 配置 ----------
SMTP_PRESETS = {
    "qq.com": {"host": "smtp.qq.com", "port": 465, "ssl": True},
    "foxmail.com": {"host": "smtp.qq.com", "port": 465, "ssl": True},
    "163.com": {"host": "smtp.163.com", "port": 465, "ssl": True},
    "126.com": {"host": "smtp.126.com", "port": 465, "ssl": True},
    "sina.com": {"host": "smtp.sina.com", "port": 465, "ssl": True},
    "sina.cn": {"host": "smtp.sina.cn", "port": 465, "ssl": True},
    "outlook.com": {"host": "smtp.office365.com", "port": 587, "ssl": False, "starttls": True},
    "hotmail.com": {"host": "smtp.office365.com", "port": 587, "ssl": False, "starttls": True},
    "gmail.com": {"host": "smtp.gmail.com", "port": 465, "ssl": True},
    "yeah.net": {"host": "smtp.yeah.net", "port": 465, "ssl": True},
    "aliyun.com": {"host": "smtp.aliyun.com", "port": 465, "ssl": True},
}


def _get_preset(email: str) -> dict | None:
    """根据邮箱地址自动匹配 SMTP 服务器配置"""
    domain = email.split("@")[-1].lower()
    return SMTP_PRESETS.get(domain)


def send_email(
    smtp_config: dict,
    to_email: str,
    subject: str,
    body: str = "",
    attachment_path: str | None = None,
) -> dict:
    """
    使用内置 SMTP 发送邮件

    smtp_config 格式:
    {
        "email": "xxx@qq.com",
        "password": "授权码",
        "host": "smtp.qq.com",   # 可选，自动推断
        "port": 465,             # 可选，自动推断
        "ssl": true              # 可选，自动推断
    }
    """
    # 优先使用 Resend API（云端部署时 SMTP 端口可能被封）
    resend_key = os.environ.get("EA_RESEND_API_KEY", "")
    if resend_key:
        from_email = os.environ.get("EA_RESEND_FROM", "EmailAssistant <onboarding@resend.dev>")
        return _send_via_resend(resend_key, from_email, to_email, subject, body)

    sender = smtp_config.get("email", "")
    password = smtp_config.get("password", "")

    if not sender or not password:
        return {"success": False, "message": "SMTP 账号未配置，请在 config.json 的 smtp 字段填写邮箱和授权码"}

    # 自动推断 SMTP 服务器
    host = smtp_config.get("host", "")
    port = smtp_config.get("port", 0)
    use_ssl = smtp_config.get("ssl", True)
    use_starttls = smtp_config.get("starttls", False)

    if not host:
        preset = _get_preset(sender)
        if preset:
            host = preset["host"]
            port = port or preset["port"]
            use_ssl = preset.get("ssl", True)
            use_starttls = preset.get("starttls", False)
        else:
            return {"success": False, "message": f"无法推断 {sender} 的 SMTP 服务器，请在 config.json 手动配置 host/port"}

    if not port:
        port = 465 if use_ssl else 587

    # 构建邮件
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body or "", "plain", "utf-8"))

    # 附件
    if attachment_path and os.path.exists(attachment_path):
        fname = os.path.basename(attachment_path)
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={fname}")
        msg.attach(part)

    # 发送
    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            if use_starttls:
                server.starttls()

        server.login(sender, password)
        server.sendmail(sender, [to_email], msg.as_string())
        server.quit()
        return {"success": True, "message": f"邮件发送成功！({sender} → {to_email})"}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "SMTP 认证失败，请检查邮箱和授权码是否正确"}
    except smtplib.SMTPConnectError as e:
        return {"success": False, "message": f"无法连接 SMTP 服务器 {host}:{port} — {e}"}
    except Exception as e:
        return {"success": False, "message": f"发送失败: {str(e)}"}

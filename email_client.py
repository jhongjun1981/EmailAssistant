"""
邮件发送客户端
优先使用内置 SMTP（独立模式），回退到 EmailMarketer API
"""
import requests
import os
from smtp_sender import send_email as smtp_send


class EmailClient:
    def __init__(self, config: dict):
        """
        config: 完整的 config.json 内容
        """
        # 内置 SMTP 配置
        self.smtp_config = config.get("smtp", {})

        # EmailMarketer 配置（回退）
        em = config.get("emailmarketer", {})
        self.em_api_url = em.get("api_url", "http://localhost:8100").rstrip("/")
        self.em_api_key = em.get("api_key", "")

        # 判断使用哪种模式
        self.use_builtin_smtp = bool(
            self.smtp_config.get("email") and self.smtp_config.get("password")
        )

    def check_health(self) -> bool:
        """检查邮件发送功能是否可用"""
        if self.use_builtin_smtp:
            return True  # 内置 SMTP 配置存在即视为可用
        try:
            resp = requests.get(
                f"{self.em_api_url}/api/v1/system/health",
                headers={"X-API-Key": self.em_api_key},
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str = "",
        attachment_path: str = None,
        smtp_account_id: int = None,
    ) -> dict:
        """发送邮件 — 优先内置 SMTP，回退 EmailMarketer"""
        if self.use_builtin_smtp:
            return smtp_send(
                smtp_config=self.smtp_config,
                to_email=to_email,
                subject=subject,
                body=body,
                attachment_path=attachment_path,
            )

        # 回退：调用 EmailMarketer API
        return self._send_via_emailmarketer(
            to_email, subject, body, attachment_path, smtp_account_id
        )

    def get_sender_email(self) -> str:
        """获取当前发件人邮箱"""
        if self.use_builtin_smtp:
            return self.smtp_config.get("email", "")
        return ""

    def get_mode_info(self) -> str:
        """返回当前使用的发送模式"""
        if self.use_builtin_smtp:
            return f"内置 SMTP ({self.smtp_config.get('email', '')})"
        return f"EmailMarketer ({self.em_api_url})"

    # ── EmailMarketer 回退 ──

    def _send_via_emailmarketer(
        self, to_email, subject, body, attachment_path, smtp_account_id
    ):
        if smtp_account_id is None:
            accounts = self._list_em_accounts()
            if not accounts:
                return {
                    "success": False,
                    "message": "邮件发送未配置。请在 config.json 的 smtp 字段配置邮箱和授权码，"
                    "或启动 EmailMarketer 服务 (localhost:8100)",
                }
            smtp_account_id = accounts[0]["id"]

        data = {
            "to_email": to_email,
            "subject": subject,
            "content": body or "",
            "smtp_account_id": str(smtp_account_id),
        }

        files_data = []
        file_handle = None
        if attachment_path and os.path.exists(attachment_path):
            fname = os.path.basename(attachment_path)
            file_handle = open(attachment_path, "rb")
            files_data = [("attachments", (fname, file_handle))]

        headers = {"X-API-Key": self.em_api_key}

        try:
            resp = requests.post(
                f"{self.em_api_url}/api/v1/system/quick-send",
                headers=headers,
                data=data,
                files=files_data if files_data else None,
                timeout=30,
            )
            if file_handle:
                file_handle.close()

            if resp.status_code == 200:
                return {"success": True, "message": "邮件发送成功！"}
            else:
                error = (
                    resp.json()
                    if resp.headers.get("content-type", "").startswith("application/json")
                    else {"detail": resp.text}
                )
                return {"success": False, "message": f"发送失败: {error}"}
        except requests.ConnectionError:
            return {
                "success": False,
                "message": "邮件发送未配置。请在 config.json 的 smtp 字段配置邮箱和授权码，"
                "或启动 EmailMarketer 服务 (localhost:8100)",
            }
        except Exception as e:
            return {"success": False, "message": f"发送出错: {str(e)}"}

    def _list_em_accounts(self) -> list:
        try:
            resp = requests.get(
                f"{self.em_api_url}/api/v1/system/smtp/accounts",
                headers={"X-API-Key": self.em_api_key},
                timeout=5,
            )
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception:
            return []

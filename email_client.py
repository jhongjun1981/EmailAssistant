"""
EmailMarketer API 客户端
"""
import requests
import os


class EmailClient:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    def check_health(self) -> bool:
        """检查API是否可用"""
        try:
            resp = requests.get(f"{self.api_url}/api/v1/system/health",
                                headers=self.headers, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def send_email(self, to_email: str, subject: str, body: str = "",
                   attachment_path: str = None, smtp_account_id: int = None) -> dict:
        """发送邮件"""
        # 先获取SMTP账号ID（如果没指定）
        if smtp_account_id is None:
            accounts = self.list_smtp_accounts()
            if not accounts:
                return {"success": False, "message": "没有配置SMTP账号，请先在EmailMarketer中添加SMTP账号"}
            smtp_account_id = accounts[0]["id"]

        # 使用 multipart/form-data 发送（API要求Form格式）
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

        headers = {"X-API-Key": self.headers["X-API-Key"]}

        try:
            resp = requests.post(
                f"{self.api_url}/api/v1/system/quick-send",
                headers=headers,
                data=data,
                files=files_data if files_data else None,
                timeout=30
            )

            if file_handle:
                file_handle.close()

            if resp.status_code == 200:
                return {"success": True, "message": "邮件发送成功！"}
            else:
                error = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"detail": resp.text}
                return {"success": False, "message": f"发送失败: {error}"}
        except requests.ConnectionError:
            return {"success": False, "message": "无法连接 EmailMarketer API，请确认服务已启动 (localhost:8100)"}
        except Exception as e:
            return {"success": False, "message": f"发送出错: {str(e)}"}

    def list_smtp_accounts(self) -> list:
        """获取SMTP账号列表"""
        try:
            resp = requests.get(f"{self.api_url}/api/v1/system/smtp/accounts",
                                headers=self.headers, timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception:
            return []

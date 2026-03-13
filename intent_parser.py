"""
可插拔意图解析引擎
支持：智谱GLM / DeepSeek / 通义千问 / Claude / 本地规则
"""
import json
import re
import os
import requests

SYSTEM_PROMPT = """你是一个智能邮件助手，可以帮用户发邮件，也可以正常聊天。

判断用户意图：
- 如果用户想发邮件，返回JSON格式：
{
    "action": "send",
    "to_email": "收件人邮箱",
    "subject": "邮件标题",
    "body": "邮件正文内容",
    "attachment": "附件文件路径（如果有）"
}
- 如果用户不是发邮件（比如打招呼、问问题、闲聊），返回：
{
    "action": "chat",
    "reply": "你的回复内容"
}

规则：
1. 如果用户没有明确标题，根据正文内容自动生成简短标题
2. 如果用户提到"桌面"上的文件，路径转换为完整路径，桌面路径为：""" + os.path.expanduser("~/Desktop") + """
3. 如果发邮件信息不完整（比如缺少收件人），将缺少的字段设为 null
4. 只返回JSON，不要任何其他文字
5. chat模式下reply用中文回复，保持友好简洁"""


CHAT_SYSTEM_PROMPT = """你是一个智能邮件助手，可以帮用户发邮件，也可以正常聊天。
你的主要功能是发送邮件，但也乐意回答用户的其他问题。
用中文回复，保持友好简洁。"""


def parse_with_llm(user_input: str, model_config: dict) -> dict:
    """通过大模型API解析意图"""
    model_key = model_config.get("_key", "")

    if model_key == "claude":
        return _parse_claude(user_input, model_config)
    else:
        return _parse_openai_compatible(user_input, model_config)


def _parse_openai_compatible(user_input: str, config: dict) -> dict:
    """OpenAI兼容格式（智谱/DeepSeek/通义千问）"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}"
    }
    payload = {
        "model": config["model_id"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.1
    }

    resp = requests.post(config["base_url"], headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    content = data["choices"][0]["message"]["content"]
    return _extract_json(content)


def _parse_claude(user_input: str, config: dict) -> dict:
    """Claude API格式"""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": config["api_key"],
        "anthropic-version": "2023-06-01"
    }
    payload = {
        "model": config["model_id"],
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_input}
        ]
    }

    resp = requests.post(config["base_url"], headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    content = data["content"][0]["text"]
    return _extract_json(content)


def parse_with_local_rules(user_input: str) -> dict:
    """本地规则解析（不需要API Key）"""
    result = {
        "action": "unknown",
        "to_email": None,
        "subject": None,
        "body": None,
        "attachment": None
    }

    text = user_input.strip()

    # 检测是否为发送意图
    send_keywords = ["发送", "发邮件", "发个", "发一个", "发一封", "寄", "发给", "邮件给", "发到", "送到"]
    is_send = any(kw in text for kw in send_keywords)
    if not is_send:
        return result

    result["action"] = "send"

    # 提取邮箱
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    if emails:
        result["to_email"] = emails[0]

    # 提取附件路径
    # 匹配 Windows 路径
    path_patterns = [
        r'附件[:：]?\s*([A-Za-z]:\\[^\s，,]+)',           # 附件:D:\xxx
        r'附件[:：]?\s*(桌面\\[^\s，,]+)',                  # 附件:桌面\xxx
        r'([A-Za-z]:\\[^\s，,]+\.[a-zA-Z]{2,5})',         # D:\xxx.jpg
        r'(桌面\\[^\s，,]+\.[a-zA-Z]{2,5})',               # 桌面\xxx.jpg
        r'(~/Desktop/[^\s，,]+)',                          # ~/Desktop/xxx
    ]
    for pattern in path_patterns:
        match = re.search(pattern, text)
        if match:
            path = match.group(1)
            # 桌面路径转换
            if path.startswith("桌面"):
                desktop = os.path.expanduser("~/Desktop")
                path = path.replace("桌面", desktop, 1)
            result["attachment"] = path
            break

    # 如果提到"桌面"但没匹配到具体文件，尝试模糊匹配
    if not result["attachment"] and "桌面" in text:
        desktop = os.path.expanduser("~/Desktop")
        # 提取可能的文件关键词
        file_keywords = re.findall(r'[的]?([^\s，,。的]+?)\s*(?:文件|图片|照片|图|文档|表格|PDF)', text)
        if file_keywords:
            keyword = file_keywords[0]
            result["attachment"] = _find_file_on_desktop(keyword, desktop)

    # 提取标题和正文（简单策略）
    # 去掉已识别的部分，剩下的作为标题/正文
    remaining = text
    for kw in send_keywords:
        remaining = remaining.replace(kw, "")
    if emails:
        remaining = remaining.replace(emails[0], "")
    if result["attachment"]:
        # 去掉路径相关文本
        for p in path_patterns:
            remaining = re.sub(p, "", remaining)
    remaining = re.sub(r'[给到一个封邮件附件桌面上的]', '', remaining).strip()
    remaining = re.sub(r'\s+', ' ', remaining).strip()

    if remaining:
        result["subject"] = remaining[:50]  # 前50字符作为标题
        result["body"] = remaining

    return result


def _find_file_on_desktop(keyword: str, desktop_path: str) -> str | None:
    """在桌面上模糊查找文件"""
    if not os.path.exists(desktop_path):
        return None

    best_match = None
    for fname in os.listdir(desktop_path):
        if keyword in fname:
            best_match = os.path.join(desktop_path, fname)
            break

    # 没找到精确匹配，返回None
    return best_match


def _extract_json(text: str) -> dict:
    """从LLM返回文本中提取JSON"""
    # 尝试直接解析
    text = text.strip()

    # 去掉markdown代码块
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试找到JSON对象
        match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    return {"action": "unknown", "error": "解析失败"}


def chat_with_llm(user_input: str, config: dict) -> str:
    """非邮件指令时，用大模型正常聊天回复"""
    model_key = config.get("model", "local")
    model_config = config.get("models", {}).get(model_key, {})

    if model_key == "local" or not model_config.get("api_key"):
        return "你好！我是邮件助手，输入包含邮箱和「发送」关键词的内容就能帮你发邮件。"

    try:
        if model_key == "claude":
            headers = {
                "Content-Type": "application/json",
                "x-api-key": model_config["api_key"],
                "anthropic-version": "2023-06-01"
            }
            payload = {
                "model": model_config["model_id"],
                "max_tokens": 1024,
                "system": CHAT_SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_input}]
            }
            resp = requests.post(model_config["base_url"], headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        else:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {model_config['api_key']}"
            }
            payload = {
                "model": model_config["model_id"],
                "messages": [
                    {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_input}
                ],
                "temperature": 0.7
            }
            resp = requests.post(model_config["base_url"], headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return "你好！我是邮件助手，有什么可以帮你的？"


def parse_intent(user_input: str, config: dict) -> dict:
    """主入口：根据配置选择解析方式"""
    model_key = config.get("model", "local")
    model_config = config.get("models", {}).get(model_key, {})
    model_config["_key"] = model_key

    # 无Key或选择本地 → 本地规则
    if model_key == "local" or not model_config.get("api_key"):
        return parse_with_local_rules(user_input)

    try:
        result = parse_with_llm(user_input, model_config)
        # 如果LLM返回了chat类型，直接返回
        if result.get("action") == "chat":
            return result
        return result
    except Exception as e:
        # LLM调用失败，回退到本地规则
        result = parse_with_local_rules(user_input)
        result["_warning"] = f"模型调用失败({str(e)})，已回退到本地规则解析"
        return result

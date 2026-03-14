"""
配置管理模块
"""
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "model": "zhipu",  # 默认智谱
    "models": {
        "zhipu": {
            "name": "智谱 GLM-4-Flash (免费)",
            "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            "model_id": "glm-4-flash",
            "api_key": ""
        },
        "deepseek": {
            "name": "DeepSeek V3",
            "base_url": "https://api.deepseek.com/v1/chat/completions",
            "model_id": "deepseek-chat",
            "api_key": ""
        },
        "qwen": {
            "name": "通义千问",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "model_id": "qwen-turbo",
            "api_key": ""
        },
        "claude": {
            "name": "Claude",
            "base_url": "https://api.anthropic.com/v1/messages",
            "model_id": "claude-sonnet-4-20250514",
            "api_key": ""
        },
        "local": {
            "name": "本地规则解析 (无需Key)",
            "base_url": "",
            "model_id": "",
            "api_key": ""
        }
    },
    "smtp": {
        "email": "",
        "password": ""
    },
    "emailmarketer": {
        "api_url": "http://localhost:8100",
        "api_key": "em-secret-2026"
    },
    "default_sender": ""
}


def _apply_env_overrides(config: dict) -> dict:
    """用环境变量覆盖配置（云部署时使用）"""
    # SMTP 配置
    smtp_email = os.environ.get("EA_SMTP_EMAIL", "")
    smtp_password = os.environ.get("EA_SMTP_PASSWORD", "")
    if smtp_email:
        config.setdefault("smtp", {})["email"] = smtp_email
    if smtp_password:
        config.setdefault("smtp", {})["password"] = smtp_password

    # LLM 模型选择和 API Key
    llm_model = os.environ.get("EA_LLM_MODEL", "")  # zhipu / deepseek / local 等
    llm_api_key = os.environ.get("EA_LLM_API_KEY", "")
    if llm_model:
        config["model"] = llm_model
    if llm_api_key:
        # 给当前选中的模型设置 key
        model_key = config.get("model", "zhipu")
        if model_key in config.get("models", {}):
            config["models"][model_key]["api_key"] = llm_api_key

    # MCP Auth Token
    auth_token = os.environ.get("EA_AUTH_TOKEN", "")
    if auth_token:
        config["mcp_auth_token"] = auth_token

    return config


def load_config():
    """加载配置（文件 + 环境变量覆盖）"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        # 合并默认配置（保留新增字段）
        config = DEFAULT_CONFIG.copy()
        config.update(saved)
        # 合并 models
        if "models" in saved:
            for k, v in DEFAULT_CONFIG["models"].items():
                if k not in config["models"]:
                    config["models"][k] = v
                else:
                    merged = v.copy()
                    merged.update(config["models"][k])
                    config["models"][k] = merged
    else:
        config = DEFAULT_CONFIG.copy()

    # 环境变量覆盖（云部署优先）
    return _apply_env_overrides(config)


def save_config(config):
    """保存配置"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_current_model_config(config):
    """获取当前选中模型的配置"""
    model_key = config.get("model", "zhipu")
    return config["models"].get(model_key, config["models"]["local"])

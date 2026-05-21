# ============================================================
# TennineClaw - 全局配置
# ============================================================
# 说明：所有配置项集中管理，便于维护和修改
# 注意：敏感信息（如 API Key）请通过环境变量设置
# ============================================================

import os
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ============================================================
# 用户持久化配置（user_config.json）
# 所有界面上修改的配置都会被保存到此文件，
# 确保重启后配置不丢失。
# ============================================================

USER_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "user_config.json")

def _load_user_config() -> dict:
    """从 user_config.json 加载用户持久化配置"""
    try:
        if os.path.exists(USER_CONFIG_FILE):
            with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_user_config(config: dict):
    """保存用户配置到 user_config.json"""
    try:
        existing = _load_user_config()
        existing.update(config)
        with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[配置] 保存 user_config.json 失败: {e}")

def _get_user_config():
    """获取持久化配置（懒加载）"""
    if not hasattr(_get_user_config, "_cache"):
        _get_user_config._cache = _load_user_config()
    return _get_user_config._cache

def _invalidate_config_cache():
    """使配置缓存失效（下次自动重载）"""
    if hasattr(_get_user_config, "_cache"):
        del _get_user_config._cache

# 模型 API 覆盖配置（持久化到 user_config.json）
def get_model_api_overrides() -> dict:
    """获取每模型 API 覆盖配置，返回 {code: {base_url, api_key}}"""
    cfg = _get_user_config()
    return cfg.get("model_api_overrides", {})

def save_model_api_override(code: str, base_url: str = "", api_key: str = ""):
    """保存单个模型的 API 覆盖配置"""
    overrides = get_model_api_overrides()
    if base_url.strip() or api_key.strip():
        overrides[code] = {
            "base_url": base_url.strip() if base_url.strip() else None,
            "api_key": api_key.strip() if api_key.strip() else None,
        }
    elif code in overrides:
        del overrides[code]  # 全部清空时移除覆盖项
    _save_user_config({"model_api_overrides": overrides})

def apply_model_api_overrides(models: list) -> list:
    """将持久化的 API 覆盖合并到模型列表中"""
    overrides = get_model_api_overrides()
    result = []
    for m in models:
        merged = dict(m)
        if m["code"] in overrides:
            ov = overrides[m["code"]]
            if ov.get("base_url"):
                merged["base_url"] = ov["base_url"]
            if ov.get("api_key"):
                merged["api_key"] = ov["api_key"]
        result.append(merged)
    return result

# 配置项获取函数：先读 user_config.json，再回退到环境变量/默认值

def get_config(key, env_key=None, default=""):
    """按优先级获取配置：user_config.json > 环境变量 > 默认值"""
    # 1. 检查持久化配置
    cfg = _get_user_config()
    if key in cfg and cfg[key]:
        return cfg[key]
    # 2. 检查环境变量
    if env_key:
        env_val = os.getenv(env_key)
        if env_val:
            return env_val
    # 3. 返回默认值
    return default

# ============================================================
# API 配置（持久化可改写）
# ============================================================
# 默认从 .env / 环境变量读取，用户可通过界面修改。
# 修改后写入 user_config.json，重启后自动恢复。

# 注意：以下 API 配置不再从 .env 读取，必须通过 Web UI 右上角模型设置页面配置。
# 配置自动持久化到 user_config.json。

API_KEY = get_config("api_key", None, "")
API_BASE_URL = get_config("api_base_url", None, "https://api.deepseek.com")
API_MODEL = get_config("api_model", None, "deepseek-v4-flash")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "60"))

# ============================================================
# 模型配置
# ============================================================
AVAILABLE_MODELS = [
    {"name": "DeepSeek V4 Flash", "code": "deepseek-v4-flash", "base_url": None, "api_key": None},
]

# ============================================================
# 上下文限制
# ============================================================
MAX_CTX_TOKENS = 524288
COMPACT_THRESHOLD = int(MAX_CTX_TOKENS * 0.8)  # 80% 时触发压缩
COMPRESS_MAX_CHARS = 32768  # 压缩后最大字符数

# ============================================================
# 运行模式
# ============================================================
MODE_SMART = 1   # 智能处理模式
MODE_PLAN = 2    # 计划驱动模式
DEFAULT_MODE = MODE_SMART

MODE_NAMES = {
    MODE_SMART: "🧠 智能模式",
    MODE_PLAN: "📋 计划模式",
}

PLAN_FILE = "plan.json"

# ============================================================
# 会话管理
# ============================================================
SESSION_SAVE_DIR = "./sessions/"
SESSION_AUTO_SAVE = True  # 每轮自动保存为独立文件（标题+时间戳命名）
SESSION_TITLE_MAX_LEN = 50

# ============================================================
# Python 环境配置（持久化）
# ============================================================
DEFAULT_PYTHON_PATH = get_config("python_env", "DEFAULT_PYTHON_PATH", "python")
DEFAULT_CONDA_ENV = get_config("conda_env", "DEFAULT_CONDA_ENV", "base")
PYTHON_ENV_MANUAL_OVERRIDE = False

# ============================================================
# Web UI 配置
# ============================================================
GRADIO_PORT = int(os.getenv("GRADIO_PORT", "7860"))
GRADIO_HOST = os.getenv("GRADIO_HOST", "127.0.0.1")
GRADIO_SHARE = os.getenv("GRADIO_SHARE", "false").lower() == "true"
GRADIO_TITLE = "TennineClaw - 智能终端助手"
GRADIO_DESCRIPTION = "基于 AI 的智能终端助手"

# ============================================================
# 日志配置
# ============================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "tennineclaw.log")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================
# 安全配置
# ============================================================
# 高危命令模式（执行前需要确认）
HIGH_RISK_PATTERNS = [
    "rm -rf",
    "del /s /q",
    "format",
    "mkfs",
    "dd if=",
    "chmod 777",
    "chown -R",
    "sudo rm",
    "sudo chmod",
    "sudo chown",
]

# ============================================================
# 功能开关
# ============================================================
COMPOSER_ENABLED = True                 # 上下文压缩开关
MICRO_COMPOSER_KEEP_ROUNDS = 8          # Micro Composer 保留轮数
MANUAL_COMPOSER_MAX_CHARS = 32768       # 手动压缩最大字符数

# ============================================================
# 超时配置（支持长时任务）
# ============================================================
REQUEST_TIMEOUT_MS = 600000  # 前端请求超时（10 分钟）
UVICORN_TIMEOUT = 86400      # 后端 uvicorn 超时（24 小时）

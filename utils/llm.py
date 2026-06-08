"""LLM 集成模块 —— DeepSeek API（OpenAI 兼容），自动加载 .env 文件"""

import os
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 自动加载项目根目录的 .env 文件
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # 也试试当前工作目录
    load_dotenv()

API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_MODEL = "deepseek-chat"
BASE_URL = "https://api.deepseek.com/v1"


def is_available() -> bool:
    return bool(os.environ.get(API_KEY_ENV))


def get_api_key() -> str | None:
    return os.environ.get(API_KEY_ENV) or None


def get_client() -> AsyncOpenAI | None:
    key = get_api_key()
    if not key:
        return None
    return AsyncOpenAI(api_key=key, base_url=BASE_URL)

"""文档逐页解析模块 —— 提取式 + 可选 LLM 增强"""

import re
from collections import Counter
from . import llm as llm_utils

_STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
    "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会",
    "着", "没有", "看", "好", "自己", "这", "他", "她", "它", "们",
    "那", "什么", "怎么", "这个", "那个", "the", "a", "an", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "can", "could", "may", "might",
    "shall", "should", "in", "on", "at", "to", "for", "of", "by",
    "with", "from", "and", "or", "but", "not", "so", "if", "as",
    "it", "this", "that", "为", "与", "及", "对", "等",
}


def extract_keywords(text: str, top_n: int = 10) -> list[dict]:
    words = re.findall(r"[\u4e00-\u9fff\w]+", text.lower())
    words = [w for w in words if len(w) > 1 and w not in _STOP_WORDS]
    counter = Counter(words)
    return [{"word": w, "freq": c} for w, c in counter.most_common(top_n)]


def _split_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[。！？.!?\n])\s*", text)
    return [s.strip() for s in raw if s.strip()]


def parse_page(text: str, page_num: int) -> dict:
    keywords = extract_keywords(text)
    sentences = _split_sentences(text)
    return {
        "page_num": page_num,
        "text_length": len(text),
        "sentence_count": len(sentences),
        "keywords": keywords,
        "preview": sentences[:5] if sentences else [],
    }


async def llm_parse_page(text: str, page_num: int) -> str:
    client = llm_utils.get_client()
    if not client:
        return "[LLM 不可用：未配置 DEEPSEEK_API_KEY]"
    from openai import APIError
    try:
        resp = await client.chat.completions.create(
            model=llm_utils.DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "你是一个专业的文档分析助手。请对文档内容进行逐页解读，说明每页的核心要点、逻辑结构和关键信息。用中文回答，保持简洁。"},
                {"role": "user", "content": f"请分析第 {page_num} 页的内容：\n\n{text}"},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        return resp.choices[0].message.content
    except APIError as e:
        return f"[LLM 调用出错] {e}"


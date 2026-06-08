"""全文总结模块 —— 提取式 + 可选 LLM 增强"""

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
    "in", "on", "at", "to", "for", "of", "by", "with", "from", "and",
    "or", "but", "not", "so", "if", "as", "it", "this", "that",
}


def _split_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[。！？.!?\n])\s*", text)
    return [s.strip() for s in raw if s.strip()]


def extractive_summarize(text: str, max_sentences: int = 5) -> dict:
    sentences = _split_sentences(text)
    if not sentences:
        return {"summary": "", "sentence_count": 0, "keywords": []}

    words = re.findall(r"[\u4e00-\u9fff\w]+", text.lower())
    words = [w for w in words if len(w) > 1 and w not in _STOP_WORDS]
    word_freq = Counter(words)
    if not word_freq:
        top = sentences[:max_sentences]
        return {
            "summary": "。".join(top) + "。" if top else "",
            "sentence_count": len(sentences),
            "keywords": [],
        }

    max_freq = max(word_freq.values())
    word_weights = {w: f / max_freq for w, f in word_freq.items()}
    scored = []
    for s in sentences:
        s_words = re.findall(r"[\u4e00-\u9fff\w]+", s.lower())
        score = sum(word_weights.get(w, 0) for w in s_words) / max(len(s_words), 1)
        scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    top_sentences = [s for _, s in scored[:max_sentences]]

    return {
        "summary": "。".join(top_sentences) + "。" if top_sentences else "",
        "sentence_count": len(sentences),
        "keywords": [{"word": w, "freq": f}
                     for w, f in word_freq.most_common(10)],
    }


async def llm_summarize(text: str, file_name: str) -> str:
    client = llm_utils.get_client()
    if not client:
        return "[LLM 不可用：未配置 DEEPSEEK_API_KEY]"
    from openai import APIError
    try:
        resp = await client.chat.completions.create(
            model=llm_utils.DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "你是一个专业的文档分析助手。请对文档内容进行全文总结，提炼核心观点、关键论据和结论。用中文回答，结构清晰，字数控制在 300 字以内。"},
                {"role": "user", "content": f"请对《{file_name}》进行全文总结：\n\n{text}"},
            ],
            temperature=0.3,
            max_tokens=800,
        )
        return resp.choices[0].message.content
    except APIError as e:
        return f"[LLM 调用出错] {e}"


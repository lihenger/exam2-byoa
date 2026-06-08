"""翻译引擎模块 —— 使用 deep-translator 调用免费 Google Translate 后端"""

from deep_translator import GoogleTranslator

_CHUNK_SIZE = 4500


def translate(text: str, target: str = "zh-CN", source: str = "auto") -> str:
    """翻译文本。"""
    if not text or not text.strip():
        return ""

    try:
        translator = GoogleTranslator(source=source, target=target)
        if len(text) > _CHUNK_SIZE:
            chunks = [text[i:i + _CHUNK_SIZE] for i in range(0, len(text), _CHUNK_SIZE)]
            results = [translator.translate(chunk) for chunk in chunks]
            return "\n".join(results)
        else:
            return translator.translate(text)
    except Exception as e:
        return f"[翻译出错] {e}"

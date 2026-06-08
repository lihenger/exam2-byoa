"""PDF 文本提取模块"""

import os
from pypdf import PdfReader


def read_pdf(path: str) -> dict:
    """读取 PDF 文件，返回按页组织的结构化内容。"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"文件不存在: {path}")

    reader = PdfReader(path)
    pages = []
    total_words = 0

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        text = text.strip()
        wc = len(text.split()) if text else 0
        total_words += wc
        pages.append({
            "page_num": i + 1,
            "text": text,
            "word_count": wc,
        })

    return {
        "file_path": os.path.abspath(path),
        "file_name": os.path.basename(path),
        "file_type": "pdf",
        "total_pages": len(pages),
        "total_words": total_words,
        "pages": pages,
    }

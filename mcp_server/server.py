"""MCP Server —— 暴露 5 个文档处理工具（纯函数，无 LLM 调用）"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from utils.pdf_reader import read_pdf
from utils.ppt_reader import read_pptx
from utils.translator import translate as _translate
from utils.parser import parse_page
from utils.summarizer import extractive_summarize
from utils.exporter import export_note as _export

mcp = FastMCP("doc-assistant")


@mcp.tool()
def read_file(path: str) -> str:
    """读取本地文档（PDF / PPTX / TXT / MD），返回结构化内容。"""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return f"[错误] 文件不存在: {path}"
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        result = read_pdf(path)
        lines = [f"## 文件: {result['file_name']}  (共 {result['total_pages']} 页)"]
        for p in result["pages"]:
            text = (p["text"][:500] + "...") if len(p["text"]) > 500 else p["text"]
            lines.append(f"\n### 第 {p['page_num']} 页  (字数: {p['word_count']})")
            lines.append(text if text else "[此页无文本内容]")
        return "\n".join(lines)
    elif ext == ".pptx":
        result = read_pptx(path)
        lines = [f"## 文件: {result['file_name']}  (共 {result['total_slides']} 张)"]
        for s in result["slides"]:
            text = (s["text"][:500] + "...") if len(s["text"]) > 500 else s["text"]
            lines.append(f"\n### 第 {s['slide_num']} 张  (元素数: {s['element_count']})")
            lines.append(text if text else "[此页无文本内容]")
        return "\n".join(lines)
    elif ext in (".txt", ".md"):
        with open(path, "r", encoding="utf-8") as f:
            fc = f.read()
        return f"## 文件: {os.path.basename(path)}\n\n{fc}"
    else:
        return f"[错误] 不支持的文件格式: {ext}"


@mcp.tool()
def translate_text(text: str, target: str = "zh-CN") -> str:
    """翻译文本（使用 Google Translate）。"""
    return _translate(text, target=target)


@mcp.tool()
def parse_document(path: str, page_start: int = 1, page_end: int = 0) -> str:
    """逐页解析文档，提取关键词和结构。"""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return f"[错误] 文件不存在: {path}"
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        doc = read_pdf(path)
        items = doc["pages"]
        total = doc["total_pages"]
    elif ext == ".pptx":
        doc = read_pptx(path)
        items = doc["slides"]
        total = doc["total_slides"]
    else:
        return "[错误] 仅支持 PDF 和 PPTX 格式的逐页解析"
    if page_end == 0 or page_end > total:
        page_end = total
    lines = [f"# 逐页解析: {os.path.basename(path)}  (共 {total} 页/张)\n"]
    for item in items:
        pn = item.get("page_num") or item.get("slide_num")
        if pn < page_start or pn > page_end:
            continue
        analysis = parse_page(item["text"], pn)
        kw_str = ", ".join(k["word"] for k in analysis["keywords"][:8])
        lines.append(f"### 第 {pn} 页")
        lines.append(f"**字数**: {analysis['text_length']}  |  **句子数**: {analysis['sentence_count']}")
        lines.append(f"**关键词**: {kw_str or '(无)'}")
        if analysis["preview"]:
            lines.append("**要点预览**:")
            for s in analysis["preview"][:3]:
                lines.append(f"- {s[:100]}")
        lines.append("")
    return "\n".join(lines) if lines else "[无解析结果]"


@mcp.tool()
def summarize_file(path: str) -> str:
    """对文档进行全文概括（抽取式摘要）。"""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return f"[错误] 文件不存在: {path}"
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        doc = read_pdf(path)
        full_text = "\n".join(p["text"] for p in doc["pages"])
        file_name = doc["file_name"]
    elif ext == ".pptx":
        doc = read_pptx(path)
        full_text = "\n".join(s["text"] for s in doc["slides"])
        file_name = doc["file_name"]
    elif ext in (".txt", ".md"):
        with open(path, "r", encoding="utf-8") as f:
            full_text = f.read()
        file_name = os.path.basename(path)
    else:
        return "[错误] 不支持的文件格式"
    if not full_text.strip():
        return "[文档无文本内容，无法总结]"
    result = extractive_summarize(full_text, max_sentences=6)
    kw_str = ", ".join(k["word"] for k in result["keywords"][:10])
    lines = [
        f"# 文档总结: {file_name}",
        f"**总句子数**: {result['sentence_count']}",
        f"**关键词**: {kw_str or '(无)'}",
        "",
        "## 提取式摘要",
        result["summary"],
    ]
    return "\n".join(lines)


@mcp.tool()
def export_note_tool(title: str, sections_json: str, output_dir: str = "output") -> str:
    """将分析结果整理为结构化的 Markdown 笔记并保存。"""
    import json
    try:
        sections = json.loads(sections_json)
    except json.JSONDecodeError as e:
        return f"[错误] sections_json 格式错误: {e}"
    filepath = _export(title, sections, output_dir)
    return f"[笔记已保存] {filepath}"


if __name__ == "__main__":
    mcp.run("stdio")

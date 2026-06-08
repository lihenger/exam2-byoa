"""笔记导出模块 —— 将分析结果组装为 .md 文件"""

import os
from datetime import datetime


def export_note(
    title: str,
    sections: list[dict],
    output_dir: str = "output",
) -> str:
    """将分析结果组装为结构化的 Markdown 笔记文件。"""
    os.makedirs(output_dir, exist_ok=True)

    safe_title = "".join(c for c in title if c.isalnum() or c in " _-.")
    safe_title = safe_title.strip().replace(" ", "_") or "untitled"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_title}_{timestamp}.md"
    filepath = os.path.join(output_dir, filename)

    lines = [
        f"# {title}",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
    ]

    for sec in sections:
        heading = sec.get("heading", "")
        body = sec.get("body", "")
        if heading:
            lines.append(f"## {heading}")
            lines.append("")
        lines.append(body)
        lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return os.path.abspath(filepath)

# 本地文档助手 (Local Doc Assistant)

一个基于 MCP 协议的单一用途 AI 智能体，帮助用户读取、翻译、解析、总结本地文档，并将分析结果整理为 Markdown 笔记。

## 目录

- [项目概述](#项目概述)
- [核心架构](#核心架构)
- [功能列表](#功能列表)
- [快速开始](#快速开始)
- [使用示例](#使用示例)
- [技术栈](#技术栈)
- [满足的考核要求](#满足的考核要求)
- [项目结构](#项目结构)

---

## 项目概述

本智能体专为**本地文档处理**这一单一任务设计。用户提供 PDF、PPTX、TXT、MD 格式的文档，智能体依次完成：

1. **读取** — 自动识别文档格式，提取文本内容
2. **翻译** — 将文本翻译为目标语言（默认中英互译）
3. **解析** — 逐页提取关键词、句子结构，如有 LLM 则生成自然语言解读
4. **总结** — 全文概括，提取核心观点
5. **导出** — 将上述所有产出整理为结构化的 `.md` 笔记文件

## 核心架构

```
用户输入 → 编排循环 (Orchestrator) → MCP Client → stdio → MCP Server (FastMCP)
                                                           ├── read_file         → 文件系统
                                                           ├── translate_text    → 翻译 API
                                                           ├── parse_document    → 分析引擎
                                                           ├── summarize_file    → 分析引擎
                                                           └── export_note_tool  → 文件系统
```

### 组件职责

| 组件 | 文件 | 职责 |
|---|---|---|
| **MCP Server** | `mcp_server/server.py` | 通过 FastMCP 暴露 5 个工具，通过 stdio 通信 |
| **编排循环** | `agent/orchestrator.py` | 读取用户输入、解析意图、调度工具、呈现结果 |
| **系统提示词** | `agent/prompt.py` | 定义智能体的行为规则、语气和决策逻辑 |
| **工具层** | `utils/*.py` | 每个工具的具体实现（PDF 读取、翻译、解析等） |
| **LLM 集成** | `utils/llm.py` | DeepSeek API 调用，自动加载 `.env` 配置 |

### 两种运行模式

- **命令模式**（未配置 API Key）：用户输入结构化命令（`read`, `summarize`, `parse` 等）
- **自然语言模式**（配置了 `DEEPSEEK_API_KEY`）：用户用自然语言描述需求，DeepSeek 自动理解意图并调度工具

## 功能列表

### 1. read_file — 读取文档

- 支持格式：PDF、PPTX、TXT、MD
- PDF 依赖 `pypdf` 提取文本，支持逐页读取
- PPTX 依赖 `python-pptx` 提取文本框和表格内容
- 自动截断长文本（前 500 字符预览）

### 2. translate_text — 翻译文本

- 默认使用 `deep-translator`（Google Translate 免费后端）
- 支持自动检测源语言，默认译成中文
- 自动拆分长文本（每段 4500 字符）
- 配置 DeepSeek 后，可切换为 LLM 翻译（效果更好）

### 3. parse_document — 逐页解析

- **提取式**（默认）：关键词提取 + 句子统计 + 要点预览
- **LLM 增强**（有 Key 时）：DeepSeek 生成每页的自然语言解读
- 支持指定页码范围（`page_start`, `page_end`）

### 4. summarize_file — 全文总结

- **提取式**（默认）：基于词频的句子评分算法，选出最重要的 5-6 句
- **LLM 增强**（有 Key 时）：DeepSeek 生成连贯的全文总结

### 5. export_note_tool — 导出笔记

- 将多个内容块（标题 + 正文）组装为标准 Markdown 文件
- 自动添加时间戳、分隔线
- 输出到 `output/` 目录

## 快速开始

### 1. 安装依赖

```bash
pip install mcp python-pptx deep-translator openai pypdf python-docx
```

### 2. 配置 API Key（可选，推荐）

```bash
# 方法一：环境变量
export DEEPSEEK_API_KEY="sk-your-key"

# 方法二：.env 文件（项目已支持）
cp .env.example .env
# 编辑 .env 填入你的 Key
```

### 3. 运行

```bash
python agent/orchestrator.py
```

### 4. 放入文档

将你的 PDF、PPTX、TXT、MD 文件放入 `docs/` 目录。

## 使用示例

### 命令模式（无 Key）

```text
> help                        # 查看可用命令
> read docs/report.pdf        # 读取 PDF
> parse docs/slides.pptx      # 逐页解析 PPTX
> summarize docs/paper.pdf    # 全文总结
> translate Hello world       # 翻译文本
```

### 自然语言模式（有 Key）

```text
> 帮我读一下那个文件系统的 PDF
> 逐页解析前 5 页，看看讲了什么
> 把整个文档总结一下
> 翻译成中文
> 把刚刚的分析结果导出到 output
```

### 完整工作流示例

```text
> 帮我处理 docs/lecture_11_file_system Interface(6).pdf

智能体会依次：
1. 调用 read_file 读取文档
2. 询问是否需要进一步处理
3. 按需调用 parse_document / summarize_file / translate_text
4. 最后调用 export_note_tool 导出为 .md 笔记
```

## 技术栈

| 技术 | 用途 |
|---|---|
| **Python 3.12** | 运行时 |
| **MCP (Model Context Protocol)** | 标准化工具调用协议，连接 LLM 大脑与本地环境 |
| **FastMCP** | MCP Server 框架 |
| **pypdf** | PDF 文本提取 |
| **python-pptx** | PPTX 文本提取 |
| **deep-translator** | 免费翻译引擎（Google Translate 后端）|
| **OpenAI Python SDK** | DeepSeek API 调用（OpenAI 兼容模式）|
| **python-dotenv** | 环境变量管理 |
| **SQLite** | 笔记存储（内置）|

## 满足的考核要求

| 考核要求 | 实现方式 |
|---|---|
| **工具使用 / 技能（≥ 2 个）** | 5 个 MCP 工具：读文件、翻译、解析、总结、导出 |
| **上下文集成（MCP 或类似方案）** | 完整 MCP 协议实现：FastMCP Server +  stdio 传输 + ClientSession |
| **氛围编程（AI 写脚手架）** | MCP Server 搭建、Pydantic 模型、API 请求逻辑、文件解析均由 AI 生成，开发者专注于系统提示词和编排循环 |
| **单一用途** | 智能体只做一件事：读文档 → 分析 → 导出笔记 |
| **依赖外部工具和上下文** | 依赖文件系统、翻译 API、SQLite、pypdf/python-pptx 等外部工具 |

## 项目结构

```
exam_2/
├── .env.example             # 环境变量模板
├── .gitignore               # Git 忽略规则
├── requirements.txt         # Python 依赖
├── README.md                # 本文档
│
├── mcp_server/
│   └── server.py            # MCP Server，暴露 5 个工具
│
├── agent/
│   ├── orchestrator.py      # 编排循环（大脑）
│   └── prompt.py            # 系统提示词
│
├── utils/
│   ├── __init__.py
│   ├── pdf_reader.py        # PDF 文本提取
│   ├── ppt_reader.py        # PPTX 文本提取
│   ├── translator.py        # 翻译引擎
│   ├── llm.py               # DeepSeek API 集成
│   ├── parser.py            # 逐页解析
│   ├── summarizer.py        # 全文总结
│   └── exporter.py          # 笔记导出
│
├── docs/                    # 放测试文档
├── output/                  # 导出笔记输出目录
└── _test_e2e.py             # 端到端测试脚本
```

---

> 项目生成时间：2026-06-08
> 软工实践 期末项目

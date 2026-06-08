"""编排循环 —— 连接 MCP 工具与用户交互，有 Key 时用 LLM 增强输出"""

import os
import sys
import json
import asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from utils import llm as llm_utils
from agent.prompt import SYSTEM_PROMPT


async def call_tool(session, name, args):
    try:
        result = await session.call_tool(name, args)
        texts = [item.text for item in result.content if hasattr(item, "text")]
        return "\n".join(texts)
    except Exception as e:
        return f"[工具调用出错] {name}: {e}"


async def enhance_output(llm_client, raw_output: str, task_desc: str) -> str:
    """用 LLM 将工具原始输出包装为自然语言。"""
    prompt = f"""你是一个文档分析助手。用户通过工具获取了以下{task_desc}。

工具输出的原始内容：
{raw_output[:3000]}

请用自然、简洁的中文重新组织这段内容，保留所有重要信息，但去掉技术性格式标记（如 **、# 等）。
直接输出处理后的内容，不要加额外评价。"""
    try:
        resp = await llm_client.chat.completions.create(
            model=llm_utils.DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=1000,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return raw_output  # fallback to raw


async def llm_translate(llm_client, text: str, target: str = "中文") -> str:
    """用 LLM 翻译文本。"""
    prompt = f"""将以下内容翻译为{target}。只输出翻译结果，不要加任何说明。

{text[:4000]}"""
    try:
        resp = await llm_client.chat.completions.create(
            model=llm_utils.DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=2000,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[翻译失败: {e}]"


async def handle_command(session, cmd):
    if cmd.lower() in ("exit", "quit"):
        print("再见！")
        return False
    if cmd.lower() in ("help", "h"):
        print("""
可用命令:
  read <路径>         读取文档
  translate <文本>    翻译文本
  parse <路径>        逐页解析
  summarize <路径>    全文总结
  tools               列出工具
  help                帮助
  exit                退出
        """)
        return True
    if cmd == "tools":
        tools = await session.list_tools()
        print("\n可用工具:")
        for t in tools.tools:
            print(f"  {t.name}: {t.description}")
        return True

    parts = cmd.strip().split(None, 1)
    action = parts[0].lower() if parts else ""
    arg = parts[1] if len(parts) > 1 else ""

    if action == "read" and arg:
        print(f"\n正在读取: {arg}")
        print(await call_tool(session, "read_file", {"path": arg}))
        return True
    if action == "translate" and arg:
        llm_client = llm_utils.get_client()
        if llm_client:
            print("\n翻译中...")
            print(await llm_translate(llm_client, arg))
        else:
            r = await call_tool(session, "translate_text", {"text": arg, "target": "zh-CN"})
            print(r)
        return True
    if action == "parse" and arg:
        print(f"\n正在解析: {arg}")
        r = await call_tool(session, "parse_document", {"path": arg})
        # Try to enhance with LLM
        llm_client = llm_utils.get_client()
        if llm_client and not r.startswith("[错误"):
            enhanced = await enhance_output(llm_client, r, "逐页解析结果")
            print(enhanced)
        else:
            print(r)
        return True
    if action == "summarize" and arg:
        print(f"\n正在总结: {arg}")
        r = await call_tool(session, "summarize_file", {"path": arg})
        llm_client = llm_utils.get_client()
        if llm_client and not r.startswith("[错误"):
            enhanced = await enhance_output(llm_client, r, "文档总结")
            print(enhanced)
        else:
            print(r)
        return True

    print(f"[未知命令: {action}] 输入 help 查看可用命令")
    return True


async def handle_llm(session, user_input):
    if user_input.lower() in ("exit", "quit"):
        print("再见！")
        return False

    llm_client = llm_utils.get_client()
    tools_info = await session.list_tools()
    tools_desc = "\n".join(f"- {t.name}: {t.description}" for t in tools_info.tools)

    # Step 1: Parse intent
    intent_prompt = f"""根据用户请求，选择要调用的工具。

可用工具:
{tools_desc}

用户: {user_input}

回复格式（仅 JSON，不要其他文字）:
{{"tool": "工具名或 null", "args": {{"参数": "值"}}, "response": "不需要工具时直接回复的内容", "next": "如果有下一步操作，描述一下"}}

注意：
- read_file 的 path 参数是文件路径
- translate_text 的 target 默认 "zh-CN"
- export_note_tool 的 sections_json 格式: [{{"heading":"标题","body":"内容"}}]
- 如果用户要求多个操作，先做第一个，回复里通过 next 描述剩下的
- 如果请求中没有给出文件路径，response 里提示需要路径
"""

    try:
        resp = await llm_client.chat.completions.create(
            model=llm_utils.DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": intent_prompt},
            ],
            temperature=0.1, max_tokens=500,
        )
        reply = resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[LLM 调用失败: {e}]")
        return await handle_command(session, user_input)

    json_str = reply
    if "```json" in json_str:
        json_str = json_str.split("```json")[1].split("```")[0]
    elif "```" in json_str:
        json_str = json_str.split("```")[1].split("```")[0]

    try:
        decision = json.loads(json_str.strip())
    except (json.JSONDecodeError, IndexError):
        print(reply)
        return True

    tool_name = decision.get("tool")
    tool_args = decision.get("args", {})
    direct_response = decision.get("response")
    next_task = decision.get("next", "")

    if direct_response:
        print(direct_response)
        return True
    if not tool_name:
        print("我没理解，能再说清楚一些吗？")
        return True

    # Step 2: Call the tool
    print(f"\n正在调用: {tool_name} ...")
    raw_result = await call_tool(session, tool_name, tool_args)
    has_error = raw_result.startswith("[错误") or raw_result.startswith("[工具调用出错")

    if has_error:
        print(raw_result)
        return True

    # Step 3: Enhance with LLM if applicable
    if tool_name in ("parse_document", "summarize_file"):
        enhanced = await enhance_output(llm_client, raw_result,
                                        "解析结果" if tool_name == "parse_document" else "文档总结")
        print(enhanced)
    elif tool_name == "translate_text" and ("翻译出错" in raw_result or "错误" in raw_result):
        # Google blocked, use LLM translation
        text_to_translate = tool_args.get("text", "")
        enhanced = await llm_translate(llm_client, text_to_translate)
        print(enhanced)
    else:
        print(raw_result)

    # Step 4: Suggest next steps
    if next_task:
        print(f"\n下一步：{next_task}")
        print("直接告诉我继续处理，或者输入你的需求。")
    elif tool_name in ("read_file", "parse_document", "summarize_file"):
        print("\n接下来你可以：翻译 / 总结 / 导出笔记，或者告诉我其他需求。")

    return True


async def main():
    print("=" * 60)
    print("  本地文档助手 (Local Doc Assistant)")
    print("  支持 PDF / PPTX / TXT / MD")
    print("=" * 60)

    llm_ok = llm_utils.is_available()
    mode = "LLM 自然语言模式" if llm_ok else "命令模式"
    print(f"\n模式: {mode}" + (" (已配置 DeepSeek)" if llm_ok else " (未配置 DEEPSEEK_API_KEY, 功能受限)"))
    print("输入 help 查看命令，exit 退出\n")

    python_exe = sys.executable
    server_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp_server", "server.py")
    server_params = StdioServerParameters(command=python_exe, args=[server_path])

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ MCP 服务器已连接\n")

                while True:
                    try:
                        inp = input("> ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\n再见！")
                        break
                    if not inp:
                        continue

                    if llm_ok:
                        cont = await handle_llm(session, inp)
                    else:
                        cont = await handle_command(session, inp)
                    if not cont:
                        break
    except FileNotFoundError:
        print(f"[错误] 找不到服务器脚本: {server_path}")
    except Exception as e:
        print(f"[错误] {e}")


if __name__ == "__main__":
    asyncio.run(main())

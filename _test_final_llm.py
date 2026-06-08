import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DOCS = os.path.join(os.path.dirname(__file__), "docs")
OUTPUT = os.path.join(os.path.dirname(__file__), "output")

async def call(session, name, args):
    result = await session.call_tool(name, args)
    return "\n".join(item.text for item in result.content if hasattr(item, "text"))

async def main():
    params = StdioServerParameters(command=sys.executable, args=[
        os.path.join(os.path.dirname(__file__), "mcp_server", "server.py")
    ])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            pdf = os.path.join(DOCS, "lecture_11_file_system Interface(6).pdf")

            print("=" * 60)
            print("  LLM-ENHANCED TOOLS (ASYNC)")
            print("=" * 60)

            # 1. LLM parse
            print("\n[1/3] LLM parse_document (page 1)")
            r = await call(session, "parse_document", {"path": pdf, "page_start": 1, "page_end": 1})
            lines = r.split("\n")
            print(f"  Output: {len(lines)} lines")
            for line in lines[:6]:
                print(f"  {line}")
            if any("LLM" in line or "核心" in line or "要点" in line for line in lines):
                print(f"  ✅ LLM output detected")
            else:
                print(f"  ⚠️  Might be extractive fallback")

            # 2. LLM summarize
            print("\n[2/3] LLM summarize_file")
            r = await call(session, "summarize_file", {"path": pdf})
            lines = r.split("\n")
            print(f"  Output: {len(lines)} lines")
            for line in lines[:6]:
                print(f"  {line}")
            if any("LLM" in line or "总结" in line for line in lines):
                print(f"  ✅ LLM output detected")
            else:
                print(f"  ⚠️  Might be extractive fallback")

            # 3. LLM translate
            print("\n[3/3] LLM translate_text")
            r = await call(session, "translate_text", {
                "text": "A file system provides a way to organize and store data on storage devices.",
                "target": "zh-CN"
            })
            print(f"  Result: {r[:100]}")
            if "翻译出错" not in r and "错误" not in r:
                print(f"  ✅ LLM translation detected")
            else:
                print(f"  ⚠️  Fallback or error")

            print("\n" + "=" * 60)
            print("  TEST COMPLETED")
            print("=" * 60)

asyncio.run(main())

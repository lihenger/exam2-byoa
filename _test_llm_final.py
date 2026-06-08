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
            print("  LLM-ENHANCED TOOLS TEST")
            print("=" * 60)

            # Test LLM parse
            print("\n[parse_document - LLM, page 1]")
            r = await call(session, "parse_document", {"path": pdf, "page_start": 1, "page_end": 1})
            for line in r.split("\n")[:8]:
                print(f"  {line}")
            print(f"  ...")

            # Test LLM summarize
            print("\n[summarize_file - LLM]")
            r = await call(session, "summarize_file", {"path": pdf})
            for line in r.split("\n")[:10]:
                print(f"  {line}")
            print(f"  ...")

            # Test LLM translate
            print("\n[translate_text - LLM fallback]")
            r = await call(session, "translate_text", {"text": "File system is the part of the OS that manages files and directories.", "target": "zh-CN"})
            for line in r.split("\n")[:3]:
                print(f"  {line}")

            print("\n" + "=" * 60)
            print("  ALL LLM TESTS COMPLETED")
            print("=" * 60)

asyncio.run(main())

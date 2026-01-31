import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.llm.client import ask_llm

async def main():
    print("🤖 Testing Ollama connection...")
    response = await ask_llm("Why is the sky blue?", max_tokens=50)
    print(f"\n📝 Response:\n{response}")

if __name__ == "__main__":
    asyncio.run(main())

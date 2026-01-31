
import asyncio
import aiohttp
import sys

# Testing the API endpoint directly to simulate frontend
async def test_ask_endpoint():
    print("Testing /api/ask endpoint...")
    url = "http://localhost:8000/api/ask"
    payload = {"question": "Why is Rust fast?"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                print(f"Status Code: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"Answer: {data.get('answer')}")
                else:
                    print(f"Error: {await response.text()}")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_ask_endpoint())

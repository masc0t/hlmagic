from hlmagic.server import system_status
import asyncio
import json

async def test():
    try:
        # Mock authenticated for the internal call
        res = await system_status(authenticated=True)
        print(json.dumps(res, indent=4))
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())

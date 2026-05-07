import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

print("Checking imports...")
from app.main import app, lifespan
print("Imports successful.")

async def test():
    print("Entering lifespan...")
    async with lifespan(app):
        print("Inside lifespan.")
        await asyncio.sleep(1)
    print("Exited lifespan.")

if __name__ == "__main__":
    asyncio.run(test())

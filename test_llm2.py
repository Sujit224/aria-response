import os, asyncio
from dotenv import load_dotenv
load_dotenv()
from langchain_groq import ChatGroq

async def test():
    llm = ChatGroq(model='llama-3.3-70b-versatile', api_key=os.getenv('GROQ_API_KEY'), temperature=0)
    try:
        res = await llm.ainvoke('hello')
        print("llama-3.3-70b-versatile SUCCESS")
    except Exception as e:
        print("ERROR llama:", e)

    llm2 = ChatGroq(model='llama-3.1-8b-instant', api_key=os.getenv('GROQ_API_KEY'), temperature=0)
    try:
        res2 = await llm2.ainvoke('hello')
        print("llama-3.1-8b-instant SUCCESS")
    except Exception as e:
        print("llama-8b error:", e)

asyncio.run(test())

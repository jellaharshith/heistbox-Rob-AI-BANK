import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Shaik\Downloads\heistbox\.env")

async def test_exact():
    gemini_key = os.getenv("GEMINI_API_KEY")
    print(f"gemini_key: '{gemini_key}'")
    parts = [{"text": "You are roasting hackathon judge 'Judge Alice' caught in a bank heist. Detect disguise cues (pixel sunglasses, hoodie, smirk, lanyard) and return JSON with keys 'alias_title', 'outfit_roast', and 'megaphone_transcript'."}]
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={gemini_key}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.request("POST", url, json={"contents": [{"parts": parts}]})
            print("Status code:", resp.status_code)
            print("Content type:", resp.headers.get("content-type"))
            print("Response:", resp.text[:400])
        except Exception as e:
            print("Exception type:", type(e).__name__, e)

asyncio.run(test_exact())

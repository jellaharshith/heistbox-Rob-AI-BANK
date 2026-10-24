import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Shaik\Downloads\heistbox\.env")

async def test_roast():
    gemini_key = os.getenv("GEMINI_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    
    parts = [{"text": "You are roasting hackathon judge 'Judge Alice' caught in a bank heist. Detect disguise cues and return JSON with keys 'alias_title', 'outfit_roast', and 'megaphone_transcript'."}]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Gemini generateContent
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
        r1 = await client.post(url, json={"contents": [{"parts": parts}]})
        print("Gemini generateContent status:", r1.status_code)
        if r1.status_code != 200:
            print("Gemini error text:", r1.text)
        else:
            print("Gemini response:", r1.json()["candidates"][0]["content"]["parts"][0]["text"][:150])
            
        # 2. Cartesia tts/bytes
        url2 = "https://api.cartesia.ai/tts/bytes"
        r2 = await client.post(
            url2,
            json={
                "model_id": "sonic-2",
                "transcript": "Step away from the keyboard! You have been busted by PostgreSQL!",
                "voice": {"mode": "id", "id": "a0e99841-438c-4a64-b679-ae501e7d6091"},
                "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": 22050},
            },
            headers={"X-API-Key": cartesia_key, "Cartesia-Version": "2024-06-10"},
        )
        print("Cartesia tts/bytes status:", r2.status_code)
        if r2.status_code != 200:
            print("Cartesia error text:", r2.text)
        else:
            print("Cartesia bytes received:", len(r2.content))

asyncio.run(test_roast())

import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(r"C:\Users\Shaik\Downloads\heistbox")
load_dotenv(r"C:\Users\Shaik\Downloads\heistbox\.env")

from integrations.router import roast_and_poster, RoastAndPosterRequest

async def run_diag():
    req = RoastAndPosterRequest(judge_name="Judge Alice")
    try:
        res = await roast_and_poster(req)
        print("Result source:", res.get("source"))
        print("Gemini live:", res.get("gemini_live"))
        print("Cartesia live:", res.get("cartesia_live"))
        print("Audio len:", len(res.get("audio_base64") or ""))
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(run_diag())

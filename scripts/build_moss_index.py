#!/usr/bin/env python3
"""
scripts/build_moss_index.py — (Re)build the Moss semantic index of labeled prompts used by
POST /api/integrations/moss-deception.

Indexes every row of training/heistguard_train.jsonl (prompt injections and benign requests from
the public datasets the HeistGuard model was trained on) into the Moss index MOSS_ATTACK_INDEX
(default "heistbox-attacks"), keeping the label and source dataset as metadata so a query's nearest
neighbours can vote on whether a new prompt looks like a known attack.

The training set's benign rows are off-topic (e.g. "Refugee crisis in Europe") while every in-domain
banking example is an attack, so on its own every honest refund looks like its nearest attack. To
fix that bias the index also holds real benign banking requests: a stratified sample (3 per intent)
of PolyAI's BANKING77 customer queries, cached in training/data/banking77_sample.json.

Usage:  uv run python scripts/build_moss_index.py [--replace] [--refresh-benign]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
TRAIN_PATH = ROOT / "training" / "heistguard_train.jsonl"
BANKING77_PATH = ROOT / "training" / "data" / "banking77_sample.json"
BANKING77_CSV_URL = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/train.csv"
INDEX_NAME = os.getenv("MOSS_ATTACK_INDEX", "heistbox-attacks")
PER_INTENT = 3


def fetch_banking77_sample() -> list[dict]:
    """Stratified sample (PER_INTENT per intent) of the real BANKING77 customer queries, from PolyAI's own CSV."""
    import csv
    import io
    import urllib.request

    with urllib.request.urlopen(BANKING77_CSV_URL, timeout=60) as resp:
        rows = csv.DictReader(io.StringIO(resp.read().decode("utf-8")))
        by_intent: dict[str, list[str]] = {}
        for r in rows:
            text = r["text"].strip()
            if text and len(by_intent.setdefault(r["category"], [])) < PER_INTENT:
                by_intent[r["category"]].append(text)
    sample = [{"intent": intent, "text": t} for intent, texts in sorted(by_intent.items()) for t in texts]
    BANKING77_PATH.write_text(json.dumps(sample, indent=1), encoding="utf-8")
    return sample


def load_docs(refresh_benign: bool):
    from inferedge_moss import DocumentInfo

    docs = []
    for n, line in enumerate(TRAIN_PATH.read_text(encoding="utf-8").splitlines()):
        row = json.loads(line)
        text = str(row.get("prompt_text", "")).strip()
        if not text:
            continue
        docs.append(
            DocumentInfo(
                id=f"hg-{n:04d}",
                text=text[:2000],
                metadata={
                    "is_malicious": "1" if row.get("is_malicious") or row.get("label") == 1 else "0",
                    "source_dataset": str(row.get("source_dataset", "unknown")),
                },
            )
        )
    banking = fetch_banking77_sample() if refresh_benign or not BANKING77_PATH.exists() else json.loads(BANKING77_PATH.read_text(encoding="utf-8"))
    for n, row in enumerate(banking):
        docs.append(
            DocumentInfo(
                id=f"b77-{n:04d}",
                text=row["text"],
                metadata={"is_malicious": "0", "source_dataset": f"PolyAI/banking77 ({row['intent']})"},
            )
        )
    return docs


async def main(replace: bool, refresh_benign: bool) -> int:
    from inferedge_moss import MossClient

    project_id = os.getenv("MOSS_PROJECT_ID", "").strip().strip('"')
    project_key = os.getenv("MOSS_PROJECT_KEY", "").strip().strip('"')
    if not project_id or not project_key:
        print("MOSS_PROJECT_ID / MOSS_PROJECT_KEY missing in .env", file=sys.stderr)
        return 1
    client = MossClient(project_id, project_key)
    existing = {i.name for i in await client.list_indexes()}
    if INDEX_NAME in existing and not replace:
        print(f"Index {INDEX_NAME!r} already exists (pass --replace to rebuild).")
        return 0
    docs = load_docs(refresh_benign)  # gather everything first so a failed download never leaves no index
    if INDEX_NAME in existing:
        await client.delete_index(INDEX_NAME)
        print(f"Deleted existing index {INDEX_NAME!r}.")
    malicious = sum(d.metadata["is_malicious"] == "1" for d in docs)
    print(f"Creating {INDEX_NAME!r} from {len(docs)} prompts ({malicious} malicious, {len(docs) - malicious} benign)...")
    await client.create_index(INDEX_NAME, docs, "moss-minilm")
    info = await client.get_index(INDEX_NAME)
    print(f"Index ready: {info}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--replace", action="store_true", help="delete and rebuild the index if it exists")
    parser.add_argument("--refresh-benign", action="store_true", help="re-download the BANKING77 benign sample")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.replace, args.refresh_benign)))

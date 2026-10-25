"""Fetch labeled injection examples, retaining provenance and deduplicating text.

Apify collects Lakera challenge prompts, which are attack attempts (not necessarily
successful attacks). Never label arbitrary scraped web pages as injections.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "training" / "data"


def text_key(text):
    return hashlib.sha256(" ".join(unicodedata.normalize("NFKC", text).casefold().split()).encode()).hexdigest()


def hf_rows(client, dataset, limit):
    rows = []
    for offset in range(0, limit, 100):
        response = client.get("https://datasets-server.huggingface.co/rows", params={
            "dataset": dataset, "config": "default", "split": "train",
            "offset": offset, "length": min(100, limit - offset),
        })
        response.raise_for_status()
        page = response.json()["rows"]
        rows.extend(item["row"] for item in page)
        if len(page) < 100:
            break
    return rows


def apify_rows(client, limit):
    token = os.getenv("APIFY_API_TOKEN") or os.getenv("APIFY_TOKEN")
    if not token:
        raise RuntimeError("APIFY_API_TOKEN is missing")
    headers = {"Authorization": f"Bearer {token}"}
    urls = ["https://datasets-server.huggingface.co/rows?dataset=Lakera%2Fmosscap_prompt_injection&config=default&split=train&offset="
            f"{offset}&length={min(100, limit-offset)}" for offset in range(0, limit, 100)]
    response = client.post("https://api.apify.com/v2/acts/apify~cheerio-scraper/runs",
        headers=headers, params={"timeout": 120, "memory": 256, "maxTotalChargeUsd": 0.25}, json={
            "startUrls": [{"url": url} for url in urls], "maxRequestsPerCrawl": len(urls),
            "maxConcurrency": 2, "additionalMimeTypes": ["application/json"],
            "pageFunction": "async function(context) { const data = JSON.parse(context.body.toString()); return data.rows.map(item => ({text: item.row.prompt, label: 1, level: item.row.level, source_url: context.request.url})); }",
        })
    response.raise_for_status()
    run = response.json()["data"]
    print("Apify collection started:", run["id"], flush=True)
    deadline = time.monotonic() + 180
    while run["status"] in {"READY", "RUNNING"} and time.monotonic() < deadline:
        time.sleep(3)
        response = client.get(f"https://api.apify.com/v2/actor-runs/{run['id']}", headers=headers)
        response.raise_for_status()
        run = response.json()["data"]
    if run["status"] != "SUCCEEDED":
        raise RuntimeError(f"Apify run {run['id']} ended with {run['status']}")
    response = client.get(f"https://api.apify.com/v2/datasets/{run['defaultDatasetId']}/items",
                          headers=headers, params={"clean": "true", "limit": limit})
    response.raise_for_status()
    return response.json(), {"run_id": run["id"], "dataset_id": run["defaultDatasetId"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hf-limit", type=int, default=2000)
    parser.add_argument("--apify-limit", type=int, default=500)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    DATA.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    records, sources = [], []
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for dataset in ["deepset/prompt-injections", "xTRam1/safe-guard-prompt-injection"]:
            rows = hf_rows(client, dataset, args.hf_limit)
            source = "huggingface/" + dataset
            sources.append({"source": source, "fetched_rows": len(rows), "fetched_at": timestamp})
            records.extend({"prompt_text": r["text"], "label": int(r["label"]), "source_dataset": source} for r in rows)
            print(source, len(rows), flush=True)
        source = "apify/Lakera/mosscap_prompt_injection"
        try:
            rows, run = apify_rows(client, args.apify_limit)
        except httpx.HTTPStatusError as exc:
            # Keep fresh HF data useful when the external account needs Console approval.
            detail = exc.response.json().get("error", {})
            rows, run = [], {"status": "unavailable", "error": detail.get("type", str(exc.response.status_code))}
            print("Apify:", run["error"], flush=True)
        sources.append({"source": source, "fetched_rows": len(rows), "fetched_at": timestamp, **run})
        records.extend({"prompt_text": r["text"], "label": 1, "source_dataset": source,
                        "source_url": r.get("source_url"), "attack_level": r.get("level")} for r in rows)
    # Preserve the local financial examples as domain data, with their existing provenance.
    path = DATA / "heistguard_train.jsonl"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            source = row.get("source_dataset", row.get("source", ""))
            if "huggingface" in source.lower() or "apify" in source.lower():
                continue
            text = row.get("prompt_text") or row.get("text")
            label = row.get("label")
            if text and label in (0, 1, "DECEPTIVE_INJECTION", "BENIGN_ENTITLEMENT"):
                records.append({"prompt_text": text, "label": int(label in (1, "DECEPTIVE_INJECTION")),
                                "source_dataset": source or "local/existing-domain-data"})
    unique, conflicts = {}, set()
    for row in records:
        text = row["prompt_text"].strip()
        if not text:
            continue
        key = text_key(text)
        if key in unique and unique[key]["label"] != row["label"]:
            conflicts.add(key)
        unique.setdefault(key, {**row, "prompt_text": text, "id": key, "is_malicious": bool(row["label"])})
    clean = [row for key, row in unique.items() if key not in conflicts]
    output = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in clean)
    path.with_suffix(".jsonl.tmp").write_text(output, encoding="utf-8")
    path.with_suffix(".jsonl.tmp").replace(path)
    manifest = {"fetched_at": timestamp, "sources": sources, "rows": len(clean),
                "conflicting_texts_removed": len(conflicts), "labels": dict(Counter(r["label"] for r in clean)),
                "provenance_breakdown": dict(Counter(r["source_dataset"] for r in clean)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (DATA / "refresh_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

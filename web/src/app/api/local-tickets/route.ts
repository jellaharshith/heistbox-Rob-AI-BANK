// Fallback for GET /api/kernel/real-tickets: serve the rows Agent 1's harvester already wrote to
// ../training/data/heistguard_train.jsonl. Only display fields are returned (no training messages).
import { readFile } from "node:fs/promises";
import path from "node:path";

const FILE = path.join(process.cwd(), "..", "training", "data", "heistguard_train.jsonl");
const KEEP = ["id", "source", "category", "label", "prompt_text", "voice_transcript", "deception_prob", "tainted_spans", "proposed_cents", "authorized_cap_cents", "green_repaired_cents", "red_stripped_cents"];

export async function GET() {
  let text: string;
  try {
    text = await readFile(FILE, "utf8");
  } catch {
    return Response.json({ tickets: [], file: null }, { status: 404 });
  }
  const tickets: Record<string, unknown>[] = [];
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue;
    try {
      const row = JSON.parse(line) as Record<string, unknown>;
      const slim: Record<string, unknown> = {};
      for (const k of KEEP) if (k in row) slim[k] = row[k];
      const wallet = typeof row.input === "string" ? row.input.match(/Dest Wallet:\s*(0x[0-9a-fA-F]+)/) : null;
      if (wallet) slim.dest_wallet = wallet[1];
      tickets.push(slim);
    } catch {
      // skip malformed line
    }
  }
  return Response.json({ tickets, file: "training/data/heistguard_train.jsonl" });
}

// Fallback for GET /api/kernel/model-lineage: report what is actually on disk under ../training.
// Hashes and counts are computed here; metrics that no file records (loss, F1) are left null.
import { createHash } from "node:crypto";
import { readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";

const ROOT = path.join(process.cwd(), "..", "training");

async function hashFile(p: string) {
  const buf = await readFile(p);
  const st = await stat(p);
  return { bytes: st.size, sha256: createHash("sha256").update(buf).digest("hex"), modified: st.mtime.toISOString() };
}

async function listFiles(dir: string, exts: string[]): Promise<string[]> {
  try {
    return (await readdir(dir)).filter((f) => exts.some((e) => f.toLowerCase().endsWith(e))).map((f) => path.join(dir, f));
  } catch {
    return [];
  }
}

export async function GET() {
  const notes: string[] = [];
  const files: { path: string; bytes: number; sha256: string; modified: string }[] = [];

  const models = await listFiles(path.join(ROOT, "models"), [".pkl", ".safetensors", ".bin", ".gguf", ".pt"]);
  for (const m of models) files.push({ path: path.relative(path.join(ROOT, ".."), m).replace(/\\/g, "/"), ...(await hashFile(m)) });
  if (!models.length) notes.push("No model checkpoint found under training/models.");

  const counts: Record<string, number> = {};
  const jsonl = path.join(ROOT, "data", "heistguard_train.jsonl");
  try {
    const text = await readFile(jsonl, "utf8");
    for (const line of text.split(/\r?\n/)) {
      if (!line.trim()) continue;
      try {
        const src = (JSON.parse(line) as { source?: unknown }).source;
        const key = typeof src === "string" ? src : "unknown";
        counts[key] = (counts[key] ?? 0) + 1;
      } catch {}
    }
    files.push({ path: "training/data/heistguard_train.jsonl", ...(await hashFile(jsonl)) });
  } catch {
    notes.push("training/data/heistguard_train.jsonl not found.");
  }

  try {
    const cfpbPath = path.join(ROOT, "data", "real_cfpb_tickets.json");
    const rows = JSON.parse(await readFile(cfpbPath, "utf8")) as unknown[];
    counts["CFPB tickets file (real_cfpb_tickets.json)"] = Array.isArray(rows) ? rows.length : 0;
    files.push({ path: "training/data/real_cfpb_tickets.json", ...(await hashFile(cfpbPath)) });
  } catch {}

  // Training metrics only if the trainer wrote them somewhere we can find.
  let loss_curve: number[] = [];
  let f1: number | null = null;
  const metricFiles = [
    ...(await listFiles(path.join(ROOT, "models"), ["metrics.json", "trainer_state.json"])),
    ...(await listFiles(ROOT, ["metrics.json"])),
  ];
  for (const mf of metricFiles) {
    try {
      const j = JSON.parse(await readFile(mf, "utf8")) as Record<string, unknown>;
      if (Array.isArray(j.loss_curve)) loss_curve = j.loss_curve.filter((v): v is number => typeof v === "number");
      if (Array.isArray(j.log_history)) loss_curve = j.log_history.map((h) => (h as { loss?: unknown }).loss).filter((v): v is number => typeof v === "number");
      if (typeof j.f1 === "number") f1 = j.f1;
      if (typeof j.eval_f1 === "number") f1 = j.eval_f1;
    } catch {}
  }
  if (!metricFiles.length) notes.push("No training metrics file (metrics.json / trainer_state.json) on disk, so loss curve and F1 are not reported.");

  const ckpt = files.find((f) => !f.path.startsWith("training/data"));
  return Response.json({
    dataset_counts: counts,
    checkpoint_path: ckpt?.path ?? null,
    checkpoint_sha256: ckpt?.sha256 ?? null,
    checkpoint_bytes: ckpt?.bytes ?? null,
    gpu: null,
    loss_curve,
    f1,
    files,
    notes,
  });
}

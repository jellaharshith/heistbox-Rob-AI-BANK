import { readFile } from "node:fs/promises";
import { networkInterfaces } from "node:os";
import path from "node:path";

export const dynamic = "force-dynamic";

function validOrigin(value: string | undefined): string | null {
  try {
    const url = new URL(value ?? "");
    return ["http:", "https:"].includes(url.protocol) ? url.origin : null;
  } catch { return null; }
}

export async function GET(request: Request) {
  let origin = validOrigin(process.env.HEISTBOX_PUBLIC_ORIGIN);
  if (!origin) {
    try {
      const share = JSON.parse((await readFile(path.join(process.cwd(), "..", "shared", "poster_share.json"), "utf8")).replace(/^\uFEFF/, ""));
      origin = validOrigin(share.origin);
    } catch {}
  }
  const here = new URL(request.url);
  if (!origin && !["localhost", "127.0.0.1", "[::1]"].includes(here.hostname)) origin = here.origin;
  if (!origin) {
    const addresses = Object.values(networkInterfaces()).flat().filter((entry) => entry?.family === "IPv4" && !entry.internal);
    const lan = addresses.find((entry) => /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(entry!.address));
    origin = lan ? `http://${lan.address}:${here.port || "3000"}` : here.origin;
  }
  return Response.json({ origin }, { headers: { "Cache-Control": "no-store" } });
}

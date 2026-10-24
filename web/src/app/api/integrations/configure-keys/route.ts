// Shadows the /api/* proxy for this one path: FastAPI's configure-keys writes .env with no auth,
// so only forward it when the browser is on the same machine as the server — never via a tunnel.
import { BACKEND, isLocalRequest } from "@/lib/server/local-only";

export async function POST(req: Request) {
  if (!isLocalRequest(req)) {
    return Response.json(
      { error: "local_only", detail: "Keys can only be configured from the machine running HeistBox (open http://localhost:3000 there)." },
      { status: 403 },
    );
  }
  const body = await req.text();
  try {
    const res = await fetch(`${BACKEND}/api/integrations/configure-keys`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
      cache: "no-store",
    });
    return new Response(await res.text(), { status: res.status, headers: { "content-type": res.headers.get("content-type") ?? "application/json" } });
  } catch {
    return Response.json({ error: "backend_unreachable", detail: `Could not reach ${BACKEND}` }, { status: 502 });
  }
}

// Server-only helper: decide whether a request originated on this machine.
// Through a tunnel (cloudflared / ngrok) requests carry forwarding headers and a public Host,
// so anything that writes secrets must refuse them.
const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]", "::1"]);
const FORWARD_HEADERS = ["x-forwarded-for", "x-forwarded-host", "x-real-ip", "cf-connecting-ip", "cf-ray", "ngrok-trace-id", "forwarded"];

export function isLocalRequest(req: Request): boolean {
  const host = (req.headers.get("host") ?? "").replace(/:\d+$/, "").toLowerCase();
  if (!LOCAL_HOSTS.has(host)) return false;
  return !FORWARD_HEADERS.some((h) => req.headers.has(h));
}

export const BACKEND = (process.env.HEISTBOX_BACKEND_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

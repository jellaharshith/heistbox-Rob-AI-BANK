import type { NextConfig } from "next";

// Single-origin proxy: the browser only ever talks to this Next server, which forwards
// /api/* and /health to the FastAPI backend. One HTTPS tunnel on :3000 then serves both.
const BACKEND = (process.env.HEISTBOX_BACKEND_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // The rewrite proxy defaults to a 30s timeout; Factory Droid patches (droid exec) can run ~2-3 minutes.
  experimental: { proxyTimeout: 200_000 },
  // Tunnel hostnames (cloudflared / ngrok) hit `next dev` from another origin.
  allowedDevOrigins: ["127.0.0.1", "10.0.0.211", "*.trycloudflare.com", "*.ngrok-free.app", "*.ngrok.app", "*.ngrok.io"],
  async rewrites() {
    return {
      beforeFiles: [],
      afterFiles: [],
      // `fallback` runs after app routes, so web-owned handlers (local-tickets, the
      // configure-keys guard, local-lineage) always win over the proxy.
      fallback: [
        { source: "/api/:path*", destination: `${BACKEND}/api/:path*` },
        { source: "/health", destination: `${BACKEND}/health` },
      ],
    };
  },
};

export default nextConfig;

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const revalidate = 0;

import { NextRequest } from "next/server";

// Proxy LangGraph API requests through the Next.js server.
// This allows us to rewrite paths for compatibility and preserve streaming.

// Use internal service base for server-side proxying
const SERVER_BASE = process.env.LANGGRAPH_API_BASE || "http://server:2024";
const AGENT_ID = process.env.NEXT_PUBLIC_AGENT_ID || process.env.AGENT_ID || "learning_agent";

async function forwardWithFallback(req: NextRequest, rawPath: string, search: string) {
  const method = req.method.toUpperCase();
  const headers = new Headers(req.headers);
  // Buffer body once for retries and search rewrite
  let bodyBuffer: ArrayBuffer | undefined = undefined;
  if (method !== "GET" && method !== "HEAD") {
    try { bodyBuffer = await req.arrayBuffer(); } catch {}
  }

  // Normalize rawPath to avoid double graph prefixing
  const isGraphScoped = rawPath.startsWith("graphs/");
  const rootPath = isGraphScoped ? rawPath.split("/").slice(2).join("/") : rawPath;

  const isSearch = rootPath === "threads/search";
  let searchQs = search;
  if (isSearch && bodyBuffer && bodyBuffer.byteLength > 0) {
    try {
      const text = new TextDecoder().decode(bodyBuffer);
      const json = JSON.parse(text);
      const params = new URLSearchParams(searchQs.replace(/^\?/, ""));
      if (json?.query) params.set("query", String(json.query));
      if (json?.limit != null) params.set("limit", String(json.limit));
      if (json?.offset != null) params.set("offset", String(json.offset));
      searchQs = `?${params.toString()}`;
    } catch {}
  }

  type Cand = { url: string; method: string; body?: ArrayBuffer };
  const cands: Cand[] = [];
  if (isSearch) {
    cands.push({ url: `${SERVER_BASE}/threads${searchQs}`, method: "GET" });
    cands.push({ url: `${SERVER_BASE}/graphs/${AGENT_ID}/threads${searchQs}`, method: "GET" });
    cands.push({ url: `${SERVER_BASE}/threads/search${search}`, method, body: bodyBuffer });
    cands.push({ url: `${SERVER_BASE}/graphs/${AGENT_ID}/threads/search${search}`, method, body: bodyBuffer });
  } else {
    cands.push({ url: `${SERVER_BASE}/${rootPath}${search}`, method, body: bodyBuffer });
    cands.push({ url: `${SERVER_BASE}/graphs/${AGENT_ID}/${rootPath}${search}`, method, body: bodyBuffer });
  }

  let lastResp: Response | null = null;
  let lastErr: unknown = null;
  for (const c of cands) {
    try {
      const init: RequestInit = {
        method: c.method,
        headers,
        body: c.method === "GET" || c.method === "HEAD" ? undefined : c.body,
        duplex: "half",
        cache: "no-store",
      } as any;
      const resp = await fetch(c.url, init);
      const unacceptable = resp.status === 404 || (isSearch && resp.status === 405);
      if (!unacceptable) { lastResp = resp; break; }
      lastResp = resp; // keep last in case all fail
    } catch (e) { lastErr = e; }
  }
  if (!lastResp) return new Response(String(lastErr ?? "Upstream error"), { status: 502 });
  // Preserve streaming for SSE by explicitly setting headers when needed
  const outHeaders = new Headers(lastResp.headers);
  const ct = outHeaders.get("content-type") || "";
  if (ct.includes("text/event-stream")) {
    outHeaders.set("Content-Type", "text/event-stream; charset=utf-8");
    outHeaders.set("Cache-Control", "no-cache, no-transform");
    outHeaders.set("Connection", "keep-alive");
    outHeaders.delete("Content-Length");
    outHeaders.set("X-Accel-Buffering", "no");
  }
  return new Response(lastResp.body, {
    status: lastResp.status,
    statusText: lastResp.statusText,
    headers: outHeaders,
  });
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const rawPath = path.join("/");
  const search = req.nextUrl.search || "";
  return forwardWithFallback(req, rawPath, search);
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const rawPath = path.join("/");
  const search = req.nextUrl.search || "";
  return forwardWithFallback(req, rawPath, search);
}

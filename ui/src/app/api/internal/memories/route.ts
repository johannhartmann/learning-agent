import { getInternalUpstreamBase } from "@/lib/environment/api";

const EMPTY = {
  memories: [],
  patterns: [],
  learning_queue: [],
};

async function fetchWithRetry(url: string, max = 5, delayMs = 500): Promise<Response | null> {
  let lastErr: unknown = null;
  for (let i = 0; i < max; i++) {
    try {
      const ctrl = new AbortController();
      const tid = setTimeout(() => ctrl.abort(), 5000);
      const resp = await fetch(url, { signal: ctrl.signal, cache: "no-store" });
      clearTimeout(tid);
      if (resp.ok) return resp;
      // For non-200, still return to surface status code
      return resp;
    } catch (e) {
      lastErr = e;
      await new Promise((r) => setTimeout(r, delayMs * Math.pow(2, i)));
    }
  }
  return null;
}

export async function GET() {
  const base = getInternalUpstreamBase();
  const url = `${base}/api/memories`;
  const resp = await fetchWithRetry(url);
  if (!resp) {
    // Upstream unavailable (e.g., DNS EAI_AGAIN or server cold); return empty payload with 200
    return new Response(JSON.stringify(EMPTY), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }
  const text = await resp.text();
  return new Response(text, {
    status: resp.status,
    headers: { "content-type": resp.headers.get("content-type") || "application/json" },
  });
}

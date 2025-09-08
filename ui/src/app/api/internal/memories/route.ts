import { getInternalUpstreamBase } from "@/lib/environment/api";

export async function GET() {
  const base = getInternalUpstreamBase();
  const resp = await fetch(`${base}/api/memories`);
  const text = await resp.text();
  return new Response(text, {
    status: resp.status,
    headers: { "content-type": resp.headers.get("content-type") || "application/json" },
  });
}


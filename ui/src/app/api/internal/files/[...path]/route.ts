import { getInternalUpstreamBase } from "@/lib/environment/api";

export async function GET(req: Request, context: { params: { path?: string[] } }) {
  const base = getInternalUpstreamBase();
  const segments = context.params.path?.join("/") ?? "";
  const url = new URL(req.url);
  const upstream = `${base}/api/files/${segments}${url.search}`;

  const resp = await fetch(upstream);
  const headers = new Headers();
  // Pass through critical headers
  const ct = resp.headers.get("content-type");
  if (ct) headers.set("content-type", ct);
  const cc = resp.headers.get("cache-control");
  if (cc) headers.set("cache-control", cc);
  const cl = resp.headers.get("content-length");
  if (cl) headers.set("content-length", cl);

  return new Response(resp.body, { status: resp.status, headers });
}


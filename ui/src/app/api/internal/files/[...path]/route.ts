import { NextRequest, NextResponse } from "next/server";

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) {
  const params = await context.params;
  const segments = params.path || [];

  // Check if first segment looks like a thread_id (UUID format)
  let threadId: string | undefined;
  let filePath: string;

  if (segments.length > 0 && segments[0].match(/^[a-f0-9-]+$/i)) {
    // First segment is thread_id
    threadId = segments[0];
    filePath = segments.slice(1).join("/");
  } else {
    // No thread_id in path
    filePath = segments.join("/");
  }

  const apiServerUrl = process.env.INTERNAL_API_BASE || "http://api-server:8001";
  const queryString = threadId ? `?thread_id=${threadId}` : "";
  const upstream = `${apiServerUrl}/api/files/${filePath}${queryString}`;

  try {
    const resp = await fetch(upstream);

    const headers = new Headers();
    const ct = resp.headers.get("content-type");
    if (ct) headers.set("content-type", ct);
    const cc = resp.headers.get("cache-control");
    if (cc) headers.set("cache-control", cc);
    const cl = resp.headers.get("content-length");
    if (cl) headers.set("content-length", cl);

    return new Response(resp.body, {
      status: resp.status,
      headers
    });
  } catch (error) {
    console.error("Error fetching file from API server:", error);
    return NextResponse.json(
      { error: "Failed to fetch file" },
      { status: 500 }
    );
  }
}

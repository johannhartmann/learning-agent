import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    // Use internal Docker network to reach api-server
    const apiServerUrl = process.env.INTERNAL_API_BASE || "http://api-server:8001";
    const response = await fetch(`${apiServerUrl}/api/learnings`);

    if (!response.ok) {
      throw new Error(`API server responded with ${response.status}`);
    }

    const data = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error("Error proxying learnings request:", error);
    return NextResponse.json(
      { error: "Failed to fetch learnings" },
      { status: 500 }
    );
  }
}

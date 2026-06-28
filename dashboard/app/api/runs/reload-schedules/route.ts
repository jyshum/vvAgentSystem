import { NextResponse } from "next/server";

const LANGGRAPH_API = process.env.LANGGRAPH_API_URL;
const LANGGRAPH_KEY = process.env.LANGGRAPH_API_KEY;

export async function POST() {
  if (!LANGGRAPH_API || !LANGGRAPH_KEY) {
    return NextResponse.json({ error: "Agent API not configured" }, { status: 503 });
  }

  try {
    const res = await fetch(`${LANGGRAPH_API}/api/reload-schedules`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${LANGGRAPH_KEY}` },
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "Could not reach agent server" }, { status: 502 });
  }
}

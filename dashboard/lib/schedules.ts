export interface Schedule {
  client_id: string;
  client_name: string;
  cycle_frequency: string;
  cycle_day: string;
  next_run: string | null;
  last_run_status: string | null;
  last_run_at: string | null;
}

/** Fetch schedules from the FastAPI agent server. Returns [] when the agent
 * API is unconfigured or unreachable — callers render nothing in that case. */
export async function fetchSchedules(): Promise<Schedule[]> {
  const api = process.env.LANGGRAPH_API_URL;
  const key = process.env.LANGGRAPH_API_KEY;
  if (!api || !key) return [];
  try {
    const res = await fetch(`${api}/api/schedules`, {
      headers: { Authorization: `Bearer ${key}` },
      cache: "no-store",
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.schedules ?? [];
  } catch {
    return [];
  }
}

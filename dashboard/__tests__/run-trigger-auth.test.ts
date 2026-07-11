import { beforeEach, describe, expect, test, vi } from "vitest";

const getUser = vi.fn();
const from = vi.fn();

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({ auth: { getUser } })),
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminClient: vi.fn(() => ({ from })),
}));

describe("POST /api/runs/trigger authorization", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    process.env.ADMIN_EMAILS = "admin@example.com";
    process.env.SUPABASE_SERVICE_ROLE_KEY = "service-role-key";
    process.env.LANGGRAPH_API_URL = "https://agent.example.com";
    process.env.LANGGRAPH_API_KEY = "agent-key";

    getUser.mockResolvedValue({
      data: { user: { id: "user-without-client-row", email: "admin@example.com" } },
      error: null,
    });

    from.mockImplementation((table: string) => {
      if (table === "client_users") {
        return {
          select: () => ({
            eq: () => ({
              single: async () => ({
                data: null,
                error: { message: "Cannot coerce the result to a single JSON object" },
              }),
            }),
          }),
        };
      }

      return {
        select: () => ({
          eq: () => ({
            single: async () => ({ data: { id: "client-1" }, error: null }),
          }),
        }),
      };
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ thread_id: "thread-1" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
    );
  });

  test("allows a configured admin without a client_users row", async () => {
    const { POST } = await import("@/app/api/runs/trigger/route");
    const request = new Request("http://localhost/api/runs/trigger", {
      method: "POST",
      body: JSON.stringify({ clientId: "client-1" }),
      headers: { "Content-Type": "application/json" },
    });

    const response = await POST(request as never);

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ ok: true, thread_id: "thread-1" });
    expect(fetch).toHaveBeenCalledOnce();
  });
});

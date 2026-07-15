import { beforeEach, describe, expect, test, vi } from "vitest";

const getUser = vi.fn();
const from = vi.fn();

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({ auth: { getUser } })),
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminClient: vi.fn(() => ({ from })),
}));

function mockClientUsersLookup(role: string | null) {
  return {
    select: () => ({
      eq: () => ({
        maybeSingle: async () => ({ data: role ? { role } : null, error: null }),
      }),
    }),
  };
}

describe("PATCH /api/admin/clients/[id]", () => {
  const updateEq = vi.fn();

  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    process.env.ADMIN_EMAILS = "admin@example.com";

    updateEq.mockReturnValue({
      select: () => ({
        single: async () => ({ data: { id: "client-1", gsc_site_url: "https://www.x.com/" }, error: null }),
      }),
    });

    from.mockImplementation((table: string) => {
      if (table === "client_users") return mockClientUsersLookup(null);
      if (table === "clients") {
        return { update: vi.fn(() => ({ eq: updateEq })) };
      }
      throw new Error(`unexpected table ${table}`);
    });
  });

  async function callPatch(body: Record<string, unknown>) {
    const { PATCH } = await import("@/app/api/admin/clients/[id]/route");
    const request = new Request("http://localhost/api/admin/clients/client-1", {
      method: "PATCH",
      body: JSON.stringify(body),
    });
    return PATCH(request, { params: Promise.resolve({ id: "client-1" }) });
  }

  test("ADMIN_EMAILS admin without client_users row can save config", async () => {
    getUser.mockResolvedValue({
      data: { user: { id: "u1", email: "admin@example.com" } },
      error: null,
    });

    const res = await callPatch({ gsc_site_url: "https://www.x.com/" });
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.gsc_site_url).toBe("https://www.x.com/");
  });

  test("non-admin gets 403", async () => {
    getUser.mockResolvedValue({
      data: { user: { id: "u2", email: "nobody@example.com" } },
      error: null,
    });

    const res = await callPatch({ gsc_site_url: "https://www.x.com/" });
    expect(res.status).toBe(403);
  });

  test("unauthenticated gets 401", async () => {
    getUser.mockResolvedValue({ data: { user: null }, error: null });
    const res = await callPatch({ gsc_site_url: "https://www.x.com/" });
    expect(res.status).toBe(401);
  });

  test("non-whitelisted fields are stripped from the update", async () => {
    getUser.mockResolvedValue({
      data: { user: { id: "u1", email: "admin@example.com" } },
      error: null,
    });

    const clientsUpdate = vi.fn(() => ({ eq: updateEq }));
    from.mockImplementation((table: string) => {
      if (table === "client_users") return mockClientUsersLookup(null);
      if (table === "clients") return { update: clientsUpdate };
      throw new Error(`unexpected table ${table}`);
    });

    const res = await callPatch({ gsc_site_url: " https://www.x.com/ ", id: "evil", created_at: "now" });
    expect(res.status).toBe(200);
    // stray whitespace trimmed — GSC property IDs must match byte-for-byte
    expect(clientsUpdate).toHaveBeenCalledWith({ gsc_site_url: "https://www.x.com/" });
  });

  test("writes platform and implementation mode but ignores schedule fields", async () => {
    getUser.mockResolvedValue({
      data: { user: { id: "u1", email: "admin@example.com" } },
      error: null,
    });

    const clientsUpdate = vi.fn(() => ({ eq: updateEq }));
    from.mockImplementation((table: string) => {
      if (table === "client_users") return mockClientUsersLookup(null);
      if (table === "clients") return { update: clientsUpdate };
      throw new Error(`unexpected table ${table}`);
    });

    const res = await callPatch({
      site_platform: "squarespace",
      implementation_mode: "copy_paste",
      cycle_frequency: "weekly",
      cycle_day: 1,
    });
    expect(res.status).toBe(200);
    expect(clientsUpdate).toHaveBeenCalledWith({
      site_platform: "squarespace",
      implementation_mode: "copy_paste",
    });
  });

  test("empty payload gets 400", async () => {
    getUser.mockResolvedValue({
      data: { user: { id: "u1", email: "admin@example.com" } },
      error: null,
    });
    const res = await callPatch({ id: "evil-only" });
    expect(res.status).toBe(400);
  });
});

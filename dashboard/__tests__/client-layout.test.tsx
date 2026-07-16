import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  clientResult: {
    data: null as {
      id: string;
      name: string;
      website_domain: string;
    } | null,
    error: null as { code: string; message: string } | null,
  },
  fromCalls: [] as string[],
  selections: [] as { table: string; columns: string }[],
  fetchSchedules: vi.fn(async () => []),
  notFound: vi.fn((): never => {
    throw new Error("NEXT_NOT_FOUND");
  }),
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminClient: () => ({
    from: (table: string) => {
      state.fromCalls.push(table);

      const builder = {
        select(columns: string) {
          state.selections.push({ table, columns });
          return builder;
        },
        eq() {
          return builder;
        },
        order() {
          return builder;
        },
        limit() {
          return Promise.resolve({ data: [], error: null });
        },
        single() {
          return Promise.resolve(state.clientResult);
        },
      };

      return builder;
    },
  }),
}));

vi.mock("@/lib/schedules", () => ({
  fetchSchedules: state.fetchSchedules,
}));

vi.mock("next/navigation", () => ({
  notFound: state.notFound,
}));

import ClientLayout from "@/app/admin/clients/[id]/layout";

const props = {
  children: null,
  params: Promise.resolve({ id: "client-1" }),
};

describe("ClientLayout", () => {
  beforeEach(() => {
    state.clientResult = {
      data: {
        id: "client-1",
        name: "BudgetYourMD",
        website_domain: "budgetyourmd.ca",
      },
      error: null,
    };
    state.fromCalls.length = 0;
    state.selections.length = 0;
    state.fetchSchedules.mockClear();
    state.notFound.mockClear();
  });

  it("selects only client columns that remain after migration 017", async () => {
    await ClientLayout(props);

    expect(state.selections.find(({ table }) => table === "clients")?.columns).toBe(
      "id, name, website_domain",
    );
  });

  it("does not query the removed legacy improvement source", async () => {
    await ClientLayout(props);

    expect(state.fromCalls).not.toContain("improvement_runs");
  });

  it("does not fetch schedules removed by the manual-run cutover", async () => {
    await ClientLayout(props);

    expect(state.fetchSchedules).not.toHaveBeenCalled();
  });

  it("surfaces database errors instead of converting them to a 404", async () => {
    state.clientResult = {
      data: null,
      error: {
        code: "42703",
        message: "column clients.cycle_frequency does not exist",
      },
    };

    await expect(ClientLayout(props)).rejects.toThrow(
      "column clients.cycle_frequency does not exist",
    );
    expect(state.notFound).not.toHaveBeenCalled();
  });

  it("still returns a 404 when the client genuinely does not exist", async () => {
    state.clientResult = {
      data: null,
      error: {
        code: "PGRST116",
        message: "JSON object requested, multiple (or no) rows returned",
      },
    };

    await expect(ClientLayout(props)).rejects.toThrow("NEXT_NOT_FOUND");
    expect(state.notFound).toHaveBeenCalledOnce();
  });
});

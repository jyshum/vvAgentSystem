// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

import { CardActions } from "@/components/audit/CardActions";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CardActions", () => {
  it("offers approve and reject for a draft_prepared card", () => {
    render(<CardActions cardId="card-1" status="draft_prepared" />);
    expect(screen.getByRole("button", { name: /approve/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /reject/i })).toBeDefined();
    expect(screen.queryByRole("button", { name: /mark applied/i })).toBeNull();
  });

  it("offers mark applied for an approved card", () => {
    render(<CardActions cardId="card-1" status="approved" />);
    expect(screen.getByRole("button", { name: /mark applied/i })).toBeDefined();
  });

  it("offers no actions for a verified card", () => {
    render(<CardActions cardId="card-1" status="verified" />);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });

  it("surfaces a stale precondition refusal instead of failing silently", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({ error: "site changed since audit" }),
      }),
    );

    render(<CardActions cardId="card-1" status="approved" />);
    fireEvent.click(screen.getByRole("button", { name: /mark applied/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toContain("site changed since audit");
    });
  });
});

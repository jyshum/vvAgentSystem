import { describe, expect, it } from "vitest";
import { mapBoardAuditCardResults } from "@/lib/board-audit-cards";

const okOpenCards = {
  data: [] as { id: string; created_at: string }[],
  error: null,
};

const okVerifiedCards = {
  data: [] as {
    id: string;
    status: string;
    created_at: string;
    applied_at: string | null;
  }[],
  error: null,
};

describe("mapBoardAuditCardResults", () => {
  it("uses applied_at for measuring while keeping open-card age on created_at", () => {
    const result = mapBoardAuditCardResults({
      openCardsResult: {
        data: [
          { id: "open-1", created_at: "2026-07-04T00:00:00Z" },
          { id: "open-2", created_at: "2026-07-05T00:00:00Z" },
        ],
        error: null,
      },
      verifiedCardsResult: {
        data: [
          {
            id: "verified-after",
            status: "verified",
            created_at: "2026-07-01T00:00:00Z",
            applied_at: "2026-07-05T00:00:00Z",
          },
          {
            id: "verified-before",
            status: "verified",
            created_at: "2026-07-04T00:00:00Z",
            applied_at: "2026-07-02T00:00:00Z",
          },
        ],
        error: null,
      },
      latestTrackerRanAt: "2026-07-03T00:00:00Z",
      nowMs: new Date("2026-07-07T00:00:00Z").getTime(),
    });

    expect(result).toEqual({
      openCount: 2,
      oldestOpenDays: 3,
      measuring: 1,
    });
  });

  it.each([
    ["open", { data: null, error: { message: "open query failed" } }, okVerifiedCards],
    ["verified", okOpenCards, { data: null, error: { message: "verified query failed" } }],
  ])("throws when the %s-card query fails", (source, openCardsResult, verifiedCardsResult) => {
    expect(() =>
      mapBoardAuditCardResults({
        openCardsResult,
        verifiedCardsResult,
        latestTrackerRanAt: "2026-07-03T00:00:00Z",
        nowMs: new Date("2026-07-07T00:00:00Z").getTime(),
      }),
    ).toThrow(`Unable to load board audit cards (${source} cards): ${source} query failed`);
  });

  it("throws when a verified card has no applied_at timestamp", () => {
    expect(() =>
      mapBoardAuditCardResults({
        openCardsResult: okOpenCards,
        verifiedCardsResult: {
          data: [
            {
              id: "verified-1",
              status: "verified",
              created_at: "2026-07-01T00:00:00Z",
              applied_at: null,
            },
          ],
          error: null,
        },
        latestTrackerRanAt: "2026-07-03T00:00:00Z",
        nowMs: new Date("2026-07-07T00:00:00Z").getTime(),
      }),
    ).toThrow("Verified technical audit action card verified-1 is missing applied_at");
  });
});

import { describe, it, expect } from "vitest";
import {
  topCompetitor,
  rankAndGap,
  engineAverageByQuery,
  biggestMovers,
  opsBadge,
  aggregateCitationRate,
  measuringCount,
} from "@/lib/derive";

const scores = {
  KinderCare: { mention_rate: 0.61 },
  Brightwheel: { mention_rate: 0.3 },
  Procare: { mention_rate: 0.42 },
};

describe("topCompetitor", () => {
  it("picks the highest aggregate rate", () => {
    expect(topCompetitor(scores)).toEqual({ name: "KinderCare", rate: 0.61 });
  });
  it("returns null when empty", () => {
    expect(topCompetitor({})).toBeNull();
    expect(topCompetitor(null)).toBeNull();
  });
});

describe("rankAndGap", () => {
  it("ranks client among competitors (1 = leader)", () => {
    // client 0.42 vs 0.61/0.3/0.42 → one strictly higher → rank 2 of 4
    expect(rankAndGap(0.42, scores)).toEqual({ rank: 2, total: 4, gapToLeader: 0.19 });
  });
  it("client leading → rank 1, zero gap", () => {
    expect(rankAndGap(0.9, scores)).toEqual({ rank: 1, total: 4, gapToLeader: 0 });
  });
  it("no competitors → rank 1 of 1", () => {
    expect(rankAndGap(0.5, {})).toEqual({ rank: 1, total: 1, gapToLeader: 0 });
  });
});

const ps = (query: string, llm: string, mention_rate: number, citation_rate = 0) =>
  ({ query, llm, mention_rate, citation_rate });

describe("engineAverageByQuery", () => {
  it("averages across engines per query", () => {
    const m = engineAverageByQuery([ps("q1", "chatgpt", 0.8, 0.5), ps("q1", "claude", 0.4, 0.25), ps("q2", "chatgpt", 0.2)]);
    expect(m.get("q1")).toEqual({ mention_rate: 0.6, citation_rate: 0.375 });
    expect(m.get("q2")).toEqual({ mention_rate: 0.2, citation_rate: 0 });
  });
});

describe("biggestMovers", () => {
  it("returns the 2 largest absolute engine-averaged changes with before/after", () => {
    const latest = [ps("up", "chatgpt", 0.9), ps("down", "chatgpt", 0.1), ps("flat", "chatgpt", 0.5)];
    const previous = [ps("up", "chatgpt", 0.4), ps("down", "chatgpt", 0.7), ps("flat", "chatgpt", 0.5)];
    const movers = biggestMovers(latest, previous);
    expect(movers).toHaveLength(2);
    expect(movers[0]).toEqual({ query: "down", before: 0.7, after: 0.1, change: -0.6 });
    expect(movers[1]).toEqual({ query: "up", before: 0.4, after: 0.9, change: 0.5 });
  });
  it("treats queries missing from previous as before=0", () => {
    const movers = biggestMovers([ps("new", "chatgpt", 0.3)], []);
    expect(movers[0]).toEqual({ query: "new", before: 0, after: 0.3, change: 0.3 });
  });
  it("empty when no previous run", () => {
    expect(biggestMovers([ps("q", "chatgpt", 0.3)], null)).toEqual([]);
  });
});

describe("opsBadge", () => {
  it("error wins over everything", () => {
    expect(opsBadge({ latestPipelineStatus: "error", pendingCount: 3, oldestPendingDays: 2, measuring: 1 }).kind).toBe("error");
  });
  it("waiting with age beats measuring", () => {
    const b = opsBadge({ latestPipelineStatus: "completed", pendingCount: 3, oldestPendingDays: 2, measuring: 1 });
    expect(b.kind).toBe("waiting");
    expect(b.label).toBe("3 CARDS · 2D");
  });
  it("measuring when implemented cards await next run", () => {
    const b = opsBadge({ latestPipelineStatus: "completed", pendingCount: 0, oldestPendingDays: null, measuring: 4 });
    expect(b.kind).toBe("measuring");
  });
  it("healthy otherwise", () => {
    expect(opsBadge({ latestPipelineStatus: "completed", pendingCount: 0, oldestPendingDays: null, measuring: 0 }).kind).toBe("healthy");
  });
});

describe("aggregateCitationRate", () => {
  it("averages citation_rate over queries with mentions only (conditional on mention)", () => {
    const m = aggregateCitationRate([ps("q1", "chatgpt", 0.6, 0.5), ps("q2", "chatgpt", 0, 0), ps("q3", "chatgpt", 0.4, 0.25)]);
    expect(m).toBeCloseTo(0.375);
  });
  it("null when nothing mentioned", () => {
    expect(aggregateCitationRate([ps("q", "chatgpt", 0, 0)])).toBeNull();
  });
});

describe("measuringCount", () => {
  it("counts implemented cards created after the latest tracker run", () => {
    const cards = [
      { status: "implemented", created_at: "2026-07-05T10:00:00Z" },
      { status: "implemented", created_at: "2026-07-01T10:00:00Z" },
      { status: "pending", created_at: "2026-07-05T10:00:00Z" },
    ];
    expect(measuringCount(cards, "2026-07-03T00:00:00Z")).toBe(1);
  });
  it("0 with no tracker run", () => {
    expect(measuringCount([{ status: "implemented", created_at: "2026-07-05T10:00:00Z" }], null)).toBe(0);
  });
});

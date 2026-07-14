import { describe, expect, it } from "vitest";
import { buildRunFunnel, runPresentationMode } from "@/lib/run-presentation";

describe("run presentation", () => {
  it("uses technical mode when a checklist run exists", () => {
    expect(runPresentationMode({ id: "audit-1" })).toBe("technical_v1");
  });

  it("does not describe matching or content gaps in technical mode", () => {
    const text = buildRunFunnel({
      mode: "technical_v1",
      technicalStatus: "completed",
      technicalChecks: 14,
      technicalFailures: 2,
      technicalReviews: 3,
      technicalUnknown: 1,
      competitorLeads: 7,
      cards: 5,
      matched: 0,
      weak: 0,
      contentGaps: 0,
      scoredPages: 0,
    });
    expect(text).toContain("14 technical checks");
    expect(text).toContain("7 measured competitor leads");
    expect(text).toContain("5 manual cards");
    expect(text).not.toMatch(/matched|weak|content gaps|scored/i);
  });

  it("shows the technical audit status before completion", () => {
    expect(
      buildRunFunnel({
        mode: "technical_v1",
        technicalStatus: "running",
        technicalChecks: 0,
        technicalFailures: 0,
        technicalReviews: 0,
        technicalUnknown: 0,
        competitorLeads: 2,
        cards: 1,
        matched: 0,
        weak: 0,
        contentGaps: 0,
        scoredPages: 0,
      }),
    ).toBe(
      "AI visibility measured → technical audit running → 2 measured competitor leads → 1 manual cards",
    );
  });

  it("preserves the legacy funnel vocabulary", () => {
    const text = buildRunFunnel({
      mode: "legacy",
      technicalStatus: null,
      technicalChecks: 0,
      technicalFailures: 0,
      technicalReviews: 0,
      technicalUnknown: 0,
      competitorLeads: 2,
      cards: 3,
      matched: 4,
      weak: 1,
      contentGaps: 2,
      scoredPages: 4,
    });
    expect(text).toContain("4 matched");
    expect(text).toContain("1 weak");
    expect(text).toContain("2 content gaps");
    expect(text).toContain("4 pages scored");
  });
});

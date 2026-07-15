import { describe, expect, it } from "vitest";
import {
  buildRunFunnel,
  crawlabilityBannerPresentation,
  runPresentationMode,
} from "@/lib/run-presentation";

describe("run presentation", () => {
  it("classifies a legacy run without an audit child as legacy", () => {
    expect(runPresentationMode({ run_mode: "legacy" })).toBe("legacy");
  });

  it("classifies a historical legacy run with an audit child as legacy", () => {
    const historicalRun = {
      run_mode: "legacy" as const,
      technicalAuditRun: { id: "older-audit-1" },
    };

    expect(runPresentationMode(historicalRun)).toBe("legacy");
  });

  it("classifies a completed technical V1 run from its persisted marker", () => {
    const completedRun = {
      run_mode: "technical_v1" as const,
      technicalAuditRun: { id: "audit-1", status: "completed" },
    };

    expect(runPresentationMode(completedRun)).toBe("technical_v1");
  });

  it("keeps technical V1 mode when no audit child exists", () => {
    const failedInitializationRun = {
      run_mode: "technical_v1" as const,
      technicalAuditRun: null,
    };

    expect(runPresentationMode(failedInitializationRun)).toBe("technical_v1");
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
      "AI visibility measured → technical audit running → 2 measured competitor leads → 1 manual card",
    );
  });

  it("shows an unavailable audit neutrally when technical V1 has no child", () => {
    expect(
      buildRunFunnel({
        mode: "technical_v1",
        technicalStatus: null,
        technicalChecks: 0,
        technicalFailures: 0,
        technicalReviews: 0,
        technicalUnknown: 0,
        competitorLeads: 0,
        cards: 0,
        matched: 9,
        weak: 2,
        contentGaps: 1,
        scoredPages: 8,
      }),
    ).toBe(
      "AI visibility measured → technical audit unavailable → 0 measured competitor leads → 0 manual cards",
    );
  });

  it.each([
    [0, "0 technical checks", "0 measured competitor leads", "0 manual cards"],
    [1, "1 technical check", "1 measured competitor lead", "1 manual card"],
    [2, "2 technical checks", "2 measured competitor leads", "2 manual cards"],
  ])(
    "formats technical funnel count grammar for %i",
    (count, checks, leads, cards) => {
      const text = buildRunFunnel({
        mode: "technical_v1",
        technicalStatus: "completed",
        technicalChecks: count,
        technicalFailures: 0,
        technicalReviews: 0,
        technicalUnknown: 0,
        competitorLeads: count,
        cards: count,
        matched: 0,
        weak: 0,
        contentGaps: 0,
        scoredPages: 0,
      });

      expect(text).toContain(checks);
      expect(text).toContain(leads);
      expect(text).toContain(cards);
      expect(text).not.toContain("1 manual cards");
    },
  );

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

  it("keeps the legacy crawlability fix-card CTA", () => {
    expect(crawlabilityBannerPresentation("legacy", "client-1")).toEqual({
      detailFallback: "see the priority-0 card for details",
      ctaLabel: "VIEW FIX-CRAWLABILITY CARD →",
      href: "/admin/approvals",
      guidance:
        "DIAGNOSIS BELOW IS THE PRE-FIX BASELINE — VISIBILITY DATA REMAINS VALID",
    });
  });

  it("uses neutral crawlability review guidance for technical V1", () => {
    const presentation = crawlabilityBannerPresentation(
      "technical_v1",
      "client-1",
    );

    expect(presentation.href).toBe("/admin/clients/client-1/runs");
    expect(presentation.ctaLabel).toBe("VIEW RUN EVIDENCE →");
    expect(presentation.detailFallback).toMatch(/review.*run evidence/i);
    expect(presentation.guidance).toMatch(/review/i);
    expect(JSON.stringify(presentation)).not.toMatch(/fix-crawlability|priority-0/i);
  });
});

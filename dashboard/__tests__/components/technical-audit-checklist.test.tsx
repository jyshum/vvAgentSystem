// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";

import { TechnicalAuditChecklist } from "@/components/runs/TechnicalAuditChecklist";
import type {
  TechnicalAuditResult,
  TechnicalAuditRun,
} from "@/lib/technical-audit-types";

const runFixture: TechnicalAuditRun = {
  id: "audit-1",
  client_id: "client-1",
  improvement_run_id: "improvement-1",
  pipeline_run_id: "pipeline-1",
  audit_version: 1,
  status: "completed",
  scope: { inventory_pages: 1, observations: 2 },
  summary: {
    pass: 1,
    fail: 0,
    review: 1,
    unknown: 1,
    not_applicable: 1,
    total: 4,
  },
  error_message: null,
  started_at: "2026-07-14T10:00:00Z",
  completed_at: "2026-07-14T10:00:02Z",
};

function result(
  status: TechnicalAuditResult["status"],
  summary: string,
): TechnicalAuditResult {
  return {
    id: `${status}-1`,
    audit_run_id: "audit-1",
    check_id: `canonical.${status}`,
    check_version: 1,
    section: "canonical_url",
    subject: "https://example.com/page",
    status,
    summary,
    expected: "One appropriate canonical declaration",
    observed: { canonicals: [] },
    evidence_refs: ["page:https://example.com/page"],
    scope: { sampled: false, urls_checked: 1 },
    applicability: { applies: status !== "not_applicable", reason: "Indexable HTML page" },
    confidence: "high",
    next_action: {
      owner: status === "pass" ? "system" : "admin",
      instruction:
        status === "review"
          ? "Add a canonical through the site's authoritative SEO setting"
          : "No action required",
    },
    remediation_id: status === "review" ? "canonical.correct" : null,
    lifecycle_state: "new",
    created_at: "2026-07-14T10:00:02Z",
  };
}

const resultFixtures = [
  result("pass", "Canonical is structurally valid"),
  result("review", "Canonical declaration is missing"),
  result("unknown", "Canonical target could not be fetched"),
  result("not_applicable", "Canonical does not apply"),
];

afterEach(cleanup);

describe("TechnicalAuditChecklist", () => {
  it("shows five status counts and no readiness score", () => {
    render(<TechnicalAuditChecklist run={runFixture} results={resultFixtures} />);

    expect(screen.getByText("Technical audit")).toBeTruthy();
    expect(screen.getByText("1 pass")).toBeTruthy();
    expect(screen.getByText("0 fail")).toBeTruthy();
    expect(screen.getByText("1 review")).toBeTruthy();
    expect(screen.getByText("1 unknown")).toBeTruthy();
    expect(screen.getByText("1 not applicable")).toBeTruthy();
    expect(screen.queryByText(/readiness/i)).toBeNull();
    expect(screen.queryByText(/\/100/)).toBeNull();
  });

  it("shows the resolution contract for a non-pass result", () => {
    render(<TechnicalAuditChecklist run={runFixture} results={resultFixtures} />);
    const summary = screen.getByText("Canonical declaration is missing");
    fireEvent.click(summary);
    const reviewResult = summary.closest("details");

    expect(reviewResult).not.toBeNull();
    expect(within(reviewResult!).getByText("Expected")).toBeTruthy();
    expect(within(reviewResult!).getByText("Why this applies")).toBeTruthy();
    expect(within(reviewResult!).getByText("Next action")).toBeTruthy();
    expect(
      within(reviewResult!).getByText(
        /Add a canonical through the site's authoritative SEO setting/,
      ),
    ).toBeTruthy();
  });

  it("renders an explicit bounded error state instead of undefined counts", () => {
    render(
      <TechnicalAuditChecklist
        run={{
          ...runFixture,
          status: "error",
          summary: {} as TechnicalAuditRun["summary"],
          error_message: "audit storage failed",
        }}
        results={[]}
      />,
    );

    expect(screen.getByText("Technical audit failed")).toBeTruthy();
    expect(screen.getByText("audit storage failed")).toBeTruthy();
    expect(screen.queryByText(/undefined/)).toBeNull();
  });

  it("renders an explicit running state without checklist counts", () => {
    render(
      <TechnicalAuditChecklist
        run={{ ...runFixture, status: "running", summary: {} as TechnicalAuditRun["summary"] }}
        results={[]}
      />,
    );

    expect(screen.getByText("Technical audit running")).toBeTruthy();
    expect(screen.queryByText(/undefined/)).toBeNull();
  });
});

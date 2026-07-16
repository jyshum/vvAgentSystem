// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { RunTechnicalAuditEvidence } from "@/components/runs/RunTechnicalAuditEvidence";
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
  scope: { inventory_pages: 1, observations: 1 },
  summary: {
    pass: 0,
    fail: 0,
    review: 1,
    unknown: 0,
    not_applicable: 0,
    total: 1,
  },
  error_message: null,
  started_at: "2026-07-14T10:00:00Z",
  completed_at: "2026-07-14T10:00:02Z",
};

const resultFixture: TechnicalAuditResult = {
  id: "review-1",
  audit_run_id: "audit-1",
  check_id: "canonical.review",
  check_version: 1,
  section: "canonical_url",
  subject: "https://example.com/page",
  status: "review",
  summary: "Canonical declaration is missing",
  expected: "One appropriate canonical declaration",
  observed: { canonicals: [] },
  evidence_refs: ["page:https://example.com/page"],
  scope: { sampled: false, urls_checked: 1 },
  applicability: { applies: true, reason: "Indexable HTML page" },
  confidence: "high",
  next_action: {
    owner: "admin",
    instruction: "Add a canonical through the authoritative SEO setting",
  },
  remediation_id: "canonical.correct",
  lifecycle_state: "new",
  created_at: "2026-07-14T10:00:02Z",
};

afterEach(cleanup);

describe("RunTechnicalAuditEvidence", () => {
  it("renders historical technical evidence without reclassifying a legacy parent", () => {
    render(
      <RunTechnicalAuditEvidence
        mode="legacy"
        run={runFixture}
        results={[resultFixture]}
      />,
    );

    expect(screen.getByText("HISTORICAL TECHNICAL CHECKLIST")).toBeTruthy();
    expect(screen.getByText("Technical audit")).toBeTruthy();
    expect(screen.getByText("Canonical declaration is missing")).toBeTruthy();
    expect(screen.getByText("1 review")).toBeTruthy();
  });

  it("renders normal technical evidence for a technical V1 parent", () => {
    render(
      <RunTechnicalAuditEvidence
        mode="technical_v1"
        run={runFixture}
        results={[resultFixture]}
      />,
    );

    expect(screen.getByText("Technical audit")).toBeTruthy();
    expect(screen.getByText("Canonical declaration is missing")).toBeTruthy();
    expect(screen.queryByText("HISTORICAL TECHNICAL CHECKLIST")).toBeNull();
    expect(screen.queryByText(/legacy/i)).toBeNull();
  });

  it("renders no checklist when the run has no technical-audit child", () => {
    const { container } = render(
      <RunTechnicalAuditEvidence
        mode="technical_v1"
        run={null}
        results={[]}
      />,
    );

    expect(container.firstChild).toBeNull();
    expect(screen.queryByText("Technical audit")).toBeNull();
    expect(screen.queryByText("HISTORICAL TECHNICAL CHECKLIST")).toBeNull();
  });
});

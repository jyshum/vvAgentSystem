// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

import { FindingsBoard } from "@/components/audit/FindingsBoard";
import type {
  TechnicalAuditActionCard,
  TechnicalAuditFindingGroup,
  TechnicalAuditResult,
  TechnicalAuditRun,
} from "@/lib/technical-audit-types";

afterEach(cleanup);

const run: TechnicalAuditRun = {
  id: "audit-1",
  client_id: "client-1",
  improvement_run_id: null,
  pipeline_run_id: null,
  audit_version: 1,
  status: "completed",
  scope: {},
  summary: { pass: 1, fail: 1, review: 0, unknown: 0, not_applicable: 1, total: 3 },
  error_message: null,
  started_at: "2026-07-16T09:00:00Z",
  completed_at: "2026-07-16T09:05:00Z",
};

const group: TechnicalAuditFindingGroup = {
  id: "group-1",
  audit_run_id: "audit-1",
  group_key: "gk-1",
  check_id: "metadata.description",
  remediation_id: "meta_description.correct",
  summary: "Meta description missing on 1 page",
  status: "fail",
  subjects: ["https://site.test/a"],
  created_at: "2026-07-16T09:00:00Z",
};

const card: TechnicalAuditActionCard = {
  id: "card-1",
  client_id: "client-1",
  audit_run_id: "audit-1",
  group_key: "gk-1",
  source: "technical",
  status: "draft_prepared",
  title: "Meta description missing",
  platform: "squarespace",
  implementation_mode: "guided",
  instructions: ["Open Page Settings then SEO."],
  copy_values: {},
  precondition: {},
  approved_by: null,
  approved_at: null,
  applied_at: null,
  verification: {},
  created_at: "2026-07-16T09:00:00Z",
  updated_at: "2026-07-16T09:00:00Z",
};

function result(overrides: Partial<TechnicalAuditResult> = {}): TechnicalAuditResult {
  return {
    id: "result-x",
    audit_run_id: "audit-1",
    check_id: "metadata.description",
    check_version: 1,
    section: "metadata",
    subject: "https://site.test/a",
    status: "fail",
    summary: "Meta description missing",
    expected: "A meta description",
    observed: {},
    evidence_refs: [],
    scope: {},
    applicability: { applies: true, reason: "public page" },
    confidence: "high",
    next_action: { owner: "admin", instruction: "Add one" },
    remediation_id: "meta_description.correct",
    lifecycle_state: "new",
    created_at: "2026-07-16T09:00:00Z",
    ...overrides,
  };
}

const naResult = result({
  id: "result-na",
  check_id: "freshness.dates",
  section: "freshness",
  subject: "https://site.test/about",
  status: "not_applicable",
  summary: "Check does not apply",
  applicability: { applies: false, reason: "Timeless/utility page with no declared date signals" },
});

const failResult = result({ id: "result-a", subject: "https://site.test/a" });

describe("FindingsBoard", () => {
  it("renders an open card's finding as a single priority row, not also as raw evidence", () => {
    const { container } = render(
      <FindingsBoard run={run} results={[failResult, naResult]} groups={[group]} cards={[card]} />,
    );
    // The carried finding shows once, as a pulsing priority row.
    const priority = container.querySelectorAll(".vv-priority");
    expect(priority).toHaveLength(1);
    expect(screen.getByText("Meta description missing on 1 page")).toBeDefined();
    // "needs action" marks the priority row; the raw fail result is not repeated.
    expect(screen.getByText(/needs action/i)).toBeDefined();
  });

  it("surfaces the not-applicable reason on the collapsed row", () => {
    render(<FindingsBoard run={run} results={[failResult, naResult]} groups={[group]} cards={[card]} />);
    // The reason appears twice: once on the collapsed summary line (the new
    // surfacing) and once in the expanded "Why this applies" evidence field.
    // A plain pass row would show it only in the expanded field.
    expect(
      screen.getAllByText("Timeless/utility page with no declared date signals"),
    ).toHaveLength(2);
  });

  it("does not promote a verified card to a priority row; its finding shows as evidence", () => {
    const { container } = render(
      <FindingsBoard
        run={run}
        results={[failResult, naResult]}
        groups={[group]}
        cards={[{ ...card, status: "verified" }]}
      />,
    );
    expect(container.querySelectorAll(".vv-priority")).toHaveLength(0);
    // The finding is no longer carried, so its raw summary is rendered instead.
    expect(screen.getByText("Meta description missing")).toBeDefined();
  });
});

// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

import { ActionCard } from "@/components/audit/ActionCard";
import type {
  TechnicalAuditActionCard,
  TechnicalAuditFindingGroup,
  TechnicalAuditResult,
} from "@/lib/technical-audit-types";

afterEach(cleanup);

const group: TechnicalAuditFindingGroup = {
  id: "group-1",
  audit_run_id: "audit-1",
  group_key: "gk-1",
  check_id: "metadata.description",
  remediation_id: "meta_description.correct",
  summary: "Meta description missing",
  status: "fail",
  subjects: ["/a", "/b", "/c", "/d"],
  created_at: "2026-07-16T09:14:00Z",
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
  instructions: ["Open Page Settings then SEO.", "Edit the SEO Description field."],
  copy_values: {},
  precondition: {},
  approved_by: null,
  approved_at: null,
  applied_at: null,
  verification: {},
  created_at: "2026-07-16T09:14:00Z",
  updated_at: "2026-07-16T09:14:00Z",
};

function result(overrides: Partial<TechnicalAuditResult> = {}): TechnicalAuditResult {
  return {
    id: "result-1",
    audit_run_id: "audit-1",
    check_id: "metadata.description",
    check_version: 1,
    section: "metadata",
    subject: "/a",
    status: "fail",
    summary: "Meta description missing",
    expected: "A meta description describing the page's own content",
    observed: { description: null },
    evidence_refs: [],
    scope: {},
    applicability: { applies: true, reason: "public page" },
    confidence: "high",
    next_action: { owner: "admin", instruction: "Add a meta description" },
    remediation_id: "meta_description.correct",
    lifecycle_state: "new",
    created_at: "2026-07-16T09:14:00Z",
    ...overrides,
  };
}

describe("ActionCard", () => {
  it("renders one card covering all grouped subjects, not one per subject", () => {
    render(<ActionCard card={card} group={group} results={[result()]} />);
    expect(screen.getByTestId("card-title").textContent).toBe("Meta description missing");
    expect(screen.getByTestId("card-subjects").textContent).toContain("4 pages");
  });

  it("leads with expected, and hides instructions behind a disclosure", () => {
    render(<ActionCard card={card} group={group} results={[result()]} />);
    expect(screen.getByTestId("card-expected").textContent).toContain(
      "A meta description describing",
    );
    expect(screen.getByText(/how to apply/i).tagName.toLowerCase()).toBe("summary");
  });

  it("renders the lifecycle chip when the finding regressed", () => {
    render(
      <ActionCard
        card={card}
        group={group}
        results={[result({ lifecycle_state: "regressed" })]}
      />,
    );
    expect(screen.getByText("regressed")).toBeDefined();
  });

  it("renders observed facts from copy_values as data", () => {
    render(
      <ActionCard
        card={{ ...card, copy_values: { broken: ["https://x.test/a", "https://x.test/b"] } }}
        group={group}
        results={[result()]}
      />,
    );
    expect(screen.getByText("https://x.test/a")).toBeDefined();
    expect(screen.getByText("https://x.test/b")).toBeDefined();
  });

  it("states the real remainder when more facts exist than are shown", () => {
    const broken = Array.from({ length: 60 }, (_, i) => `https://x.test/${i}`);
    render(
      <ActionCard
        card={{ ...card, copy_values: { broken } }}
        group={group}
        results={[result()]}
      />,
    );
    // Only the first 10 are listed, but the operator is told the true scope.
    expect(screen.getByText("https://x.test/9")).toBeDefined();
    expect(screen.queryByText("https://x.test/10")).toBeNull();
    expect(screen.getByTestId("card-facts-remainder").textContent).toBe(
      "Showing 10 of 60",
    );
  });

  it("keys repeated facts uniquely so React does not warn", () => {
    // Guards the list key itself. React renders duplicate-keyed siblings on
    // first mount either way, so a row count cannot detect this - the warning
    // is the only observable difference, and it flags undefined reconciliation
    // behaviour on refresh.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ActionCard
        card={{ ...card, copy_values: { broken: ["https://x.test/dead", "https://x.test/dead"] } }}
        group={group}
        results={[result()]}
      />,
    );
    const duplicateKeyWarnings = spy.mock.calls.filter((args) =>
      String(args[0]).includes("same key"),
    );
    spy.mockRestore();
    expect(duplicateKeyWarnings).toHaveLength(0);
  });

  it("renders every occurrence when the same fact repeats", () => {
    // One page can link to the same dead URL twice (nav and footer), so
    // copy_values arrays are not deduplicated upstream. Guards against anyone
    // "fixing" duplicates with a Set, which would understate the true count.
    const broken = [
      "https://x.test/dead",
      "https://x.test/dead",
      "https://x.test/other",
    ];
    render(
      <ActionCard
        card={{ ...card, copy_values: { broken } }}
        group={group}
        results={[result()]}
      />,
    );
    // Both occurrences render: a dropped row would understate the true count.
    expect(screen.getAllByText("https://x.test/dead")).toHaveLength(2);
    expect(within(screen.getByTestId("card-facts")).getAllByRole("listitem")).toHaveLength(
      3,
    );
  });

  it("counts repeated facts once each in the remainder total", () => {
    const broken = [
      ...Array.from({ length: 11 }, () => "https://x.test/dead"),
      "https://x.test/other",
    ];
    render(
      <ActionCard
        card={{ ...card, copy_values: { broken } }}
        group={group}
        results={[result()]}
      />,
    );
    // 12 real facts, 10 shown - the indicator must reflect occurrences, not
    // distinct values, or it would disagree with the rows above it.
    expect(within(screen.getByTestId("card-facts")).getAllByRole("listitem")).toHaveLength(
      10,
    );
    expect(screen.getByTestId("card-facts-remainder").textContent).toBe(
      "Showing 10 of 12",
    );
  });

  it("omits the remainder indicator when every fact is shown", () => {
    const broken = Array.from({ length: 10 }, (_, i) => `https://x.test/${i}`);
    render(
      <ActionCard
        card={{ ...card, copy_values: { broken } }}
        group={group}
        results={[result()]}
      />,
    );
    expect(screen.getByText("https://x.test/9")).toBeDefined();
    expect(screen.queryByTestId("card-facts-remainder")).toBeNull();
  });
});

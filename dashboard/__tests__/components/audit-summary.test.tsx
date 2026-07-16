// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

import { AuditSummary } from "@/components/audit/AuditSummary";
import type { TechnicalAuditRun } from "@/lib/technical-audit-types";

afterEach(cleanup);

const run: TechnicalAuditRun = {
  id: "audit-1",
  client_id: "client-1",
  improvement_run_id: null,
  pipeline_run_id: null,
  audit_version: 1,
  status: "completed",
  scope: {},
  summary: { pass: 196, fail: 12, review: 3, unknown: 2, not_applicable: 4, total: 217 },
  error_message: null,
  started_at: "2026-07-16T09:14:00Z",
  completed_at: "2026-07-16T09:16:00Z",
};

describe("AuditSummary", () => {
  it("renders every status count including unknown", () => {
    render(<AuditSummary run={run} clientId="client-1" domain="example.com" />);
    expect(screen.getByText("12 fail")).toBeDefined();
    expect(screen.getByText("2 unknown")).toBeDefined();
    expect(screen.getByText("196 pass")).toBeDefined();
  });

  it("shows the check total", () => {
    render(<AuditSummary run={run} clientId="client-1" domain="example.com" />);
    expect(screen.getByTestId("audit-meta").textContent).toContain("217 checks");
  });

  it("renders no score anywhere", () => {
    const { container } = render(
      <AuditSummary run={run} clientId="client-1" domain="example.com" />,
    );
    expect(container.textContent).not.toContain("/100");
  });
});

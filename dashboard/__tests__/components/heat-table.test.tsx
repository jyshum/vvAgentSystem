// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { HeatTable } from "@/components/admin/HeatTable";

const row = {
  queryId: "query-1",
  query: "best daycare software",
  paraphrases: ["top childcare apps"],
  version: 2,
  cells: [
    { runId: "r1", ranAt: "2026-06-23", rate: 0.2 },
    { runId: "r2", ranAt: "2026-06-30", rate: 0.6 },
  ],
  stability: "gaining",
  citedPct: 0.25,
  page: { url: "https://x.com/guide", similarity: 0.82, weak: false },
  topCompetitor: { name: "KinderCare", rate: 0.61 },
  waiting: 2,
};

describe("HeatTable", () => {
  it("renders query, rates, stability, cited, page, competitor, waiting", () => {
    render(<HeatTable rows={[row]} clientId="c1" />);
    expect(screen.getByText("best daycare software")).toBeTruthy();
    expect(screen.getByText("20%")).toBeTruthy();
    expect(screen.getByText("60%")).toBeTruthy();
    expect(screen.getByText(/gaining/i)).toBeTruthy();
    expect(screen.getByText("25%")).toBeTruthy();
    expect(screen.getByText(/KinderCare/)).toBeTruthy();
    expect(screen.getByText(/2 PENDING/)).toBeTruthy();
  });
  it("pending badge deep-links to approvals filtered by query", () => {
    render(<HeatTable rows={[row]} clientId="c1" />);
    const badges = screen.getAllByText(/2 PENDING/) as HTMLAnchorElement[];
    expect(badges.at(-1)!.getAttribute("href")).toBe("/admin/approvals?query=query-1");
  });
  it("flags weak matches", () => {
    render(<HeatTable rows={[{ ...row, page: { ...row.page!, weak: true } }]} clientId="c1" />);
    expect(screen.getByText(/WEAK/)).toBeTruthy();
  });
  it("renders dash when no page match", () => {
    render(<HeatTable rows={[{ ...row, page: null, waiting: 0 }]} clientId="c1" />);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});

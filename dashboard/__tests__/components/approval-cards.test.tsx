// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AutomatedCard } from "@/components/approvals/AutomatedCard";
import { BriefCard } from "@/components/approvals/BriefCard";
import { CommunityCheckCard } from "@/components/approvals/CommunityCheckCard";
import { CrawlabilityCard } from "@/components/approvals/CrawlabilityCard";
import type { ActionCard } from "@/lib/improvement-types";

const baseCard: ActionCard & { queryText: string | null } = {
  id: "card-1",
  run_id: "run-1",
  client_id: "client-1",
  query_id: "q-1",
  page_url: "https://nova.example/pricing",
  action_type: "restructure_intro",
  pillar: "content",
  score: 42,
  track: "automated",
  priority: 1,
  competitive_gap: 0.4,
  structural_score: 42,
  issue: "Page opens with filler, no direct answer to the query.",
  before_text: "Welcome to Nova! We're so glad you're here.",
  after_text: "Nova is a CRM built for consultancies of 2-20 people.",
  code_block: "",
  status: "pending",
  cms_action: "wordpress_api",
  auto_approved: false,
  validation_passed: true,
  verification: null,
  brief: null,
  reddit_data: null,
  preview_url: null,
  created_at: "2026-07-03T10:00:00Z",
  queryText: "best crm for startups",
};

describe("AutomatedCard", () => {
  it("renders issue, before/after, and calls onDecide on APPROVE", () => {
    const onDecide = vi.fn();
    render(<AutomatedCard card={baseCard} decision={undefined} onDecide={onDecide} />);
    expect(screen.getByText(baseCard.issue)).toBeTruthy();
    expect(screen.getByText(baseCard.before_text)).toBeTruthy();
    expect(screen.getByText(baseCard.after_text)).toBeTruthy();
    expect(screen.getByText("REJECT")).toBeTruthy();
    fireEvent.click(screen.getByText("APPROVE"));
    expect(onDecide).toHaveBeenCalledWith("card-1", "approved");
  });
});

describe("BriefCard", () => {
  it("renders brief document and ACCEPT & ASSIGN", () => {
    const card = {
      ...baseCard,
      id: "card-2",
      action_type: "content_brief",
      brief: {
        target_query: "crm migration checklist",
        competitive_landscape: "CompetitorA at 45%, you absent",
        recommended_title: "CRM Migration Checklist — Complete Guide",
        recommended_h1: "CRM Migration Checklist",
        key_sections: ["Direct answer up top", "Comparison table of migration paths"],
        facts_to_include: ["Industry stats with sources"],
        schema_type: "Article",
        internal_link_targets: ["/pricing"],
        word_count_target: 2000,
      },
    };
    render(<BriefCard card={card} decision={undefined} onDecide={vi.fn()} />);
    expect(screen.getByText("CRM Migration Checklist — Complete Guide")).toBeTruthy();
    expect(screen.getByText("Direct answer up top")).toBeTruthy();
    expect(screen.getByText("ACCEPT & ASSIGN")).toBeTruthy();
  });
});

describe("CommunityCheckCard", () => {
  it("renders search links with correct hrefs, MARK DONE and SKIP", () => {
    const card = {
      ...baseCard,
      id: "card-3",
      action_type: "community_check",
      reddit_data: {
        search_links: {
          reddit: "https://reddit.com/search?q=best+crm",
          google: "https://google.com/search?q=site:reddit.com+best+crm",
        },
        guidance: "Look for whether Nova is ever mentioned.",
      },
    };
    render(<CommunityCheckCard card={card} decision={undefined} onDecide={vi.fn()} />);
    const redditLink = screen.getByText(/SEARCH REDDIT/).closest("a");
    const googleLink = screen.getByText(/GOOGLE SITE:REDDIT/).closest("a");
    expect(redditLink?.getAttribute("href")).toBe("https://reddit.com/search?q=best+crm");
    expect(googleLink?.getAttribute("href")).toBe("https://google.com/search?q=site:reddit.com+best+crm");
    expect(screen.getByText("MARK DONE")).toBeTruthy();
    expect(screen.getByText("SKIP")).toBeTruthy();
  });
});

describe("CrawlabilityCard", () => {
  it("renders the issue and PRIORITY 0", () => {
    const card = {
      ...baseCard,
      id: "card-4",
      action_type: "fix_crawlability",
      priority: 0,
      issue: "robots.txt blocks GPTBot from the entire site.",
    };
    render(<CrawlabilityCard card={card} decision={undefined} onDecide={vi.fn()} />);
    expect(screen.getByText("robots.txt blocks GPTBot from the entire site.")).toBeTruthy();
    expect(screen.getByText("PRIORITY 0")).toBeTruthy();
  });
});

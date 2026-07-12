"use client";

import { useState } from "react";
import { MONO_LABEL, type Decision, type ReviewCard } from "./card-shared";
import { AutomatedCard } from "./AutomatedCard";
import { BriefCard } from "./BriefCard";
import { CommunityCheckCard } from "./CommunityCheckCard";
import { CrawlabilityCard } from "./CrawlabilityCard";

export interface InboxGroupData {
  runId: string;
  threadId: string | null;
  clientName: string;
  cmsType: string;
  waitDays: number;
  contextStrip: string | null;
  cards: ReviewCard[]; // review items, oldest first
  autoApproved: { id: string; action_type: string }[];
}

const CMS_CONSEQUENCE: Record<string, string> = {
  wordpress: "WORDPRESS — changes go live on approve",
  shopify: "SHOPIFY — changes go live on approve",
  github: "GITHUB — opens a PR, you merge",
  webflow: "WEBFLOW — staged, you publish",
};

export function InboxGroup({ group }: { group: InboxGroupData }) {
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDecide = (cardId: string, decision: Decision) => {
    setDecisions((prev) => ({ ...prev, [cardId]: decision }));
  };

  const approvedIds = group.cards.filter((c) => decisions[c.id] === "approved").map((c) => c.id);
  const rejectedIds = group.cards.filter((c) => decisions[c.id] === "rejected").map((c) => c.id);
  const undecided = group.cards.length - Object.keys(decisions).length;

  const consequence = CMS_CONSEQUENCE[group.cmsType] ?? "COPY_PASTE — manual apply";

  async function finalize() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/admin/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          threadId: group.threadId,
          approvedCardIds: approvedIds,
          rejectedCardIds: rejectedIds,
        }),
      });
      if (res.ok) {
        setSubmitted(true);
      } else {
        const body = await res.json().catch(() => ({}));
        setError(body.error || "Finalize failed.");
        setSubmitting(false);
      }
    } catch {
      setError("Finalize failed.");
      setSubmitting(false);
    }
  }

  return (
    <section id={`run-${group.runId}`} className="p-6 mb-8" style={{ border: "1px solid var(--hair)" }}>
      <div className="mb-5">
        <div className="font-display text-[20px] font-light mb-1" style={{ color: "var(--white)" }}>
          {group.clientName}
        </div>
        <div className="font-mono text-[9px] mb-1" style={{ color: "var(--mute)" }}>
          {group.cards.length} CARDS · WAITING {group.waitDays}D
        </div>
        <div className={MONO_LABEL} style={{ color: "var(--faint)" }}>
          {consequence}
        </div>
        {group.contextStrip && (
          <p className="font-serif italic text-[13px] mt-2" style={{ color: "var(--mute)" }}>
            {group.contextStrip}
          </p>
        )}
      </div>

      {submitted ? (
        <p className="font-serif italic" style={{ color: "var(--pos)" }}>
          {approvedIds.length} approved · {rejectedIds.length} rejected — sent to implementation.
        </p>
      ) : (
        <>
          <div className="space-y-4 my-5">
            {group.cards.map((card) => {
              const cardProps = { card, decision: decisions[card.id], onDecide };
              const inner = (() => {
                switch (card.action_type) {
                  case "content_brief":
                    return <BriefCard {...cardProps} />;
                  case "community_check":
                  case "reddit_engagement":
                    return <CommunityCheckCard {...cardProps} />;
                  case "fix_crawlability":
                    return <CrawlabilityCard {...cardProps} />;
                  default:
                    return <AutomatedCard {...cardProps} />;
                }
              })();
              return (
                // Anchor for deep links from the queries tab (?query=<id>):
                // CardHighlighter scrolls to and highlights matching cards.
                <div key={card.id} id={`card-${card.id}`} data-query-id={card.query_id ?? ""}>
                  {inner}
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <div className="font-mono text-[9px] mb-1" style={{ color: "var(--mute)" }}>
                {approvedIds.length} approved · {rejectedIds.length} rejected · {undecided} undecided
              </div>
              {group.autoApproved.length > 0 && (
                <p className="font-serif italic text-[12px]" style={{ color: "var(--faint)" }}>
                  {group.autoApproved.length} cards auto-approved — implement on finalize (
                  {group.autoApproved.map((a) => a.action_type).join(", ")})
                </p>
              )}
              {error && (
                <div className="font-mono text-[9px] mt-1" style={{ color: "var(--neg)" }}>
                  {error}
                </div>
              )}
              {group.threadId === null && (
                <div className="font-mono text-[8px] mt-1" style={{ color: "var(--neg)" }}>
                  THREAD UNRESOLVED — RESUME FROM SERVER
                </div>
              )}
            </div>
            <button
              onClick={finalize}
              disabled={submitting || Object.keys(decisions).length < group.cards.length || group.threadId === null}
              className="font-mono text-[10px] tracking-[0.1em] uppercase py-3 px-7 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              style={{ background: "var(--pos)", color: "var(--ink)", border: "none" }}
            >
              {submitting ? "IMPLEMENTING..." : `FINALIZE RUN (${approvedIds.length} APPROVE / ${rejectedIds.length} REJECT)`}
            </button>
          </div>
        </>
      )}
    </section>
  );
}

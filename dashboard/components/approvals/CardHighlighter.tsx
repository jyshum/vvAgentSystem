"use client";

import { useEffect } from "react";

const HIGHLIGHT_BG = "rgba(245,244,241,0.08)";
const HIGHLIGHT_MS = 4000;

/**
 * Deep-link handler for /admin/approvals?query=<queryId>.
 * Scrolls to the first pending card for that query and grey-highlights
 * every card belonging to it, fading back out after a few seconds.
 */
export function CardHighlighter() {
  useEffect(() => {
    const queryId = new URLSearchParams(window.location.search).get("query");
    if (!queryId) return;

    const escaped =
      typeof CSS !== "undefined" && typeof CSS.escape === "function"
        ? CSS.escape(queryId)
        : queryId.replace(/["\\]/g, "\\$&");
    const targets = Array.from(
      document.querySelectorAll<HTMLElement>(`[data-query-id="${escaped}"]`)
    );
    if (targets.length === 0) return;

    targets[0].scrollIntoView({ behavior: "smooth", block: "center" });

    for (const el of targets) {
      el.style.transition = "background-color 0.4s ease";
      el.style.backgroundColor = HIGHLIGHT_BG;
    }
    const timer = setTimeout(() => {
      for (const el of targets) {
        el.style.backgroundColor = "transparent";
      }
    }, HIGHLIGHT_MS);

    return () => clearTimeout(timer);
  }, []);

  return null;
}

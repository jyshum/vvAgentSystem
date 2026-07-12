import { describe, it, expect } from "vitest";
import {
  extractMentionSentence,
  pickRepresentative,
  aggregateCompetitorMentions,
  extractAllMentionEvidence,
} from "@/lib/mention";

describe("aggregateCompetitorMentions", () => {
  it("unions competitor names across rows with counts, sorted desc", () => {
    const rows = [
      { competitor_mentions: ["YNAB", "MD Financial Management"] },
      { competitor_mentions: ["YNAB"] },
      { competitor_mentions: null },
      { competitor_mentions: [] },
    ];
    expect(aggregateCompetitorMentions(rows)).toEqual([
      { name: "YNAB", count: 2 },
      { name: "MD Financial Management", count: 1 },
    ]);
  });
  it("empty when no rows mention competitors", () => {
    expect(aggregateCompetitorMentions([{ competitor_mentions: null }])).toEqual([]);
    expect(aggregateCompetitorMentions([])).toEqual([]);
  });
});

describe("extractAllMentionEvidence", () => {
  const rows = [
    {
      brand_mentioned: true,
      query: "wording A",
      response_text: "Intro. Brightwheel is great for daycares. Outro.",
    },
    {
      brand_mentioned: false,
      query: "wording B",
      response_text: "Brightwheel never mind this row is unmentioned.",
    },
    {
      brand_mentioned: true,
      query: "wording C",
      response_text: "Try bright wheel today.",
    },
  ];
  it("returns one evidence item per mentioned row, tagged with its wording", () => {
    const out = extractAllMentionEvidence(rows, ["Brightwheel", "bright wheel"]);
    expect(out).toEqual([
      {
        wording: "wording A",
        sentence: "Brightwheel is great for daycares.",
        brand: "Brightwheel",
      },
      {
        wording: "wording C",
        sentence: "Try bright wheel today.",
        brand: "bright wheel",
      },
    ]);
  });
  it("skips mentioned rows where no sentence can be extracted", () => {
    const out = extractAllMentionEvidence(
      [{ brand_mentioned: true, query: "w", response_text: "no brand here." }],
      ["Brightwheel"],
    );
    expect(out).toEqual([]);
  });
});

describe("extractMentionSentence", () => {
  const text =
    "There are many options. Brightwheel is a popular choice for daycare management! Some prefer others. What about pricing?";
  it("finds the sentence containing a brand variation", () => {
    const r = extractMentionSentence(text, ["Brightwheel"]);
    expect(r).toEqual({
      sentence: "Brightwheel is a popular choice for daycare management!",
      brand: "Brightwheel",
    });
  });
  it("is case-insensitive and tries variations in order", () => {
    const r = extractMentionSentence("we like BRIGHT WHEEL a lot.", ["Brightwheel", "bright wheel"]);
    expect(r?.brand).toBe("bright wheel");
  });
  it("first-listed variation wins when multiple variations match", () => {
    const r = extractMentionSentence("we love brightwheel here.", ["brightwheel", "bright"]);
    expect(r?.brand).toBe("brightwheel");
  });
  it("null when absent or empty", () => {
    expect(extractMentionSentence("Nothing here.", ["Brightwheel"])).toBeNull();
    expect(extractMentionSentence("", ["Brightwheel"])).toBeNull();
    expect(extractMentionSentence("text", [])).toBeNull();
  });
  it("handles text without terminal punctuation", () => {
    const r = extractMentionSentence("brands: brightwheel, procare", ["Brightwheel"]);
    expect(r?.sentence).toBe("brands: brightwheel, procare");
  });
});

describe("pickRepresentative", () => {
  const rows = [
    { brand_mentioned: false, queried_at: "2026-07-05T10:00:00Z" },
    { brand_mentioned: true, queried_at: "2026-07-03T10:00:00Z" },
    { brand_mentioned: true, queried_at: "2026-07-04T10:00:00Z" },
  ];
  it("most recent mentioned wins", () => {
    expect(pickRepresentative(rows)?.queried_at).toBe("2026-07-04T10:00:00Z");
  });
  it("falls back to most recent overall", () => {
    const none = rows.map((r) => ({ ...r, brand_mentioned: false }));
    expect(pickRepresentative(none)?.queried_at).toBe("2026-07-05T10:00:00Z");
  });
  it("null on empty", () => {
    expect(pickRepresentative([])).toBeNull();
  });
});

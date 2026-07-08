import { describe, it, expect } from "vitest";
import { extractMentionSentence, pickRepresentative } from "@/lib/mention";

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

import { describe, it, expect } from "vitest";
import {
  scoreColor,
  formatRate,
  formatDelta,
  weekRangeLabel,
  scoreLevel,
  getMentionLevelLabel,
  getMentionLevelColor,
  formatMentionLevel,
} from "@/lib/utils";

describe("scoreColor", () => {
  it("returns neg for 0", () => {
    expect(scoreColor(0)).toBe("var(--neg)");
  });
  it("returns orange for low rates", () => {
    expect(scoreColor(0.1)).toBe("#fd7e14");
  });
  it("returns yellow for mid rates", () => {
    expect(scoreColor(0.3)).toBe("#ffc107");
  });
  it("returns pos for high rates", () => {
    expect(scoreColor(0.6)).toBe("var(--pos)");
  });
});

describe("scoreLevel", () => {
  it("returns 'zero' for 0", () => {
    expect(scoreLevel(0)).toBe("zero");
  });
  it("returns 'low' for <25%", () => {
    expect(scoreLevel(0.15)).toBe("low");
  });
  it("returns 'mid' for <50%", () => {
    expect(scoreLevel(0.4)).toBe("mid");
  });
  it("returns 'high' for >=50%", () => {
    expect(scoreLevel(0.75)).toBe("high");
  });
});

describe("formatRate", () => {
  it("formats 0.05 as 5%", () => {
    expect(formatRate(0.05)).toBe("5%");
  });
  it("formats 0 as 0%", () => {
    expect(formatRate(0)).toBe("0%");
  });
  it("formats 1 as 100%", () => {
    expect(formatRate(1)).toBe("100%");
  });
  it("formats 0.253 as 25%", () => {
    expect(formatRate(0.253)).toBe("25%");
  });
});

describe("formatDelta", () => {
  it("returns positive delta with arrow", () => {
    expect(formatDelta(0.1, 0.05)).toEqual({
      text: "+5pp",
      direction: "up",
    });
  });
  it("returns negative delta with arrow", () => {
    expect(formatDelta(0.05, 0.1)).toEqual({
      text: "-5pp",
      direction: "down",
    });
  });
  it("returns flat for no change", () => {
    expect(formatDelta(0.1, 0.1)).toEqual({
      text: "±0pp",
      direction: "flat",
    });
  });
  it("returns null when no previous value", () => {
    expect(formatDelta(0.1, null)).toBeNull();
  });
});

describe("weekRangeLabel", () => {
  it("formats a week range", () => {
    const label = weekRangeLabel("2026-06-15");
    expect(label).toContain("June 15");
    expect(label).toContain("21");
  });
  it("returns empty string for null", () => {
    expect(weekRangeLabel(null)).toBe("");
  });
});

describe("getMentionLevelLabel", () => {
  it("returns Not Mentioned for 0", () => {
    expect(getMentionLevelLabel(0)).toBe("Not Mentioned");
  });
  it("returns Passing Mention for 1", () => {
    expect(getMentionLevelLabel(1)).toBe("Passing Mention");
  });
  it("returns Listed with Context for 2", () => {
    expect(getMentionLevelLabel(2)).toBe("Listed with Context");
  });
  it("returns Recommended for 3", () => {
    expect(getMentionLevelLabel(3)).toBe("Recommended");
  });
  it("returns Primary Recommendation for 4", () => {
    expect(getMentionLevelLabel(4)).toBe("Primary Recommendation");
  });
});

describe("getMentionLevelColor", () => {
  it("returns red for 0", () => {
    expect(getMentionLevelColor(0)).toBe("var(--neg)");
  });
  it("returns orange for 1", () => {
    expect(getMentionLevelColor(1)).toBe("#fd7e14");
  });
  it("returns yellow for 2", () => {
    expect(getMentionLevelColor(2)).toBe("#ffc107");
  });
  it("returns pos for 3+", () => {
    expect(getMentionLevelColor(3)).toBe("var(--pos)");
    expect(getMentionLevelColor(4)).toBe("var(--pos)");
  });
});

describe("formatMentionLevel", () => {
  it("formats level with label", () => {
    expect(formatMentionLevel(2.8)).toBe("2.8");
  });
  it("formats zero", () => {
    expect(formatMentionLevel(0)).toBe("0.0");
  });
});

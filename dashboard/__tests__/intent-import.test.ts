import { describe, expect, it } from "vitest";
import { parseIntentJson } from "@/lib/intent-import";

describe("parseIntentJson", () => {
  it("parses product visibility and content authority intents", () => {
    expect(
      parseIntentJson(
        JSON.stringify([
          {
            prompt_text: "best budgeting app",
            bucket: "consideration",
            paraphrases: ["budgeting app for med students"],
          },
          {
            prompt_text: "how to budget",
            bucket: "awareness",
            paraphrases: ["budgeting tips"],
          },
        ])
      )
    ).toEqual([
      {
        prompt_text: "best budgeting app",
        bucket: "consideration",
        paraphrases: ["budgeting app for med students"],
      },
      {
        prompt_text: "how to budget",
        bucket: "awareness",
        paraphrases: ["budgeting tips"],
      },
    ]);
  });

  it("rejects invalid buckets", () => {
    expect(() =>
      parseIntentJson(
        JSON.stringify([
          {
            prompt_text: "best budgeting app",
            bucket: "product_visibility",
            paraphrases: [],
          },
        ])
      )
    ).toThrow("invalid bucket");
  });

  it("rejects non-string paraphrases", () => {
    expect(() =>
      parseIntentJson(
        JSON.stringify([
          {
            prompt_text: "best budgeting app",
            bucket: "consideration",
            paraphrases: [7],
          },
        ])
      )
    ).toThrow("paraphrases");
  });
});

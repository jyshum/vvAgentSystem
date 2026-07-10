import { describe, expect, it } from "vitest";
import { buildIntentImportRows, parseIntentJson } from "@/lib/intent-import";

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

  it("rejects an empty imported intent set", () => {
    expect(() => parseIntentJson("[]")).toThrow("at least one intent");
    expect(() => buildIntentImportRows("client-1", [])).toThrow("at least one intent");
  });

  it("builds insert rows with slugs, defaults, and paraphrases", () => {
    expect(
      buildIntentImportRows("client-1", [
        {
          prompt_text: " Best Budgeting App ",
          paraphrases: [" app for budgets "],
        },
        {
          prompt_text: "how to budget",
          bucket: "awareness",
        },
      ])
    ).toEqual([
      {
        client_id: "client-1",
        prompt_text: "Best Budgeting App",
        slug: "best_budgeting_app_v1",
        bucket: "consideration",
        set_type: "core",
        paraphrases: ["app for budgets"],
      },
      {
        client_id: "client-1",
        prompt_text: "how to budget",
        slug: "how_to_budget_v1",
        bucket: "awareness",
        set_type: "core",
        paraphrases: [],
      },
    ]);
  });

  it("rejects an invalid intent before returning any insert rows", () => {
    expect(() =>
      buildIntentImportRows("client-1", [
        {
          prompt_text: "best budgeting app",
          bucket: "consideration",
        },
        {
          prompt_text: "bad row",
          bucket: "nope",
        },
      ])
    ).toThrow("invalid bucket");
  });
});

import { describe, expect, it } from "vitest";
import { buildIntentImportRows, parseIntentJson } from "@/lib/intent-import";

describe("parseIntentJson", () => {
  it("safely retries JSON that uses smart double quotes", () => {
    expect(
      parseIntentJson(
        '[{“prompt_text”:“donate wedding flowers”,“bucket”:“consideration”,“paraphrases”:[“reuse event flowers”]}]'
      )
    ).toEqual([
      {
        prompt_text: "donate wedding flowers",
        bucket: "consideration",
        paraphrases: ["reuse event flowers"],
      },
    ]);
  });

  it("preserves smart quotes inside already-valid JSON strings", () => {
    expect(
      parseIntentJson(
        JSON.stringify([
          {
            prompt_text: "What does “flower reuse” mean?",
            bucket: "awareness",
            paraphrases: [],
          },
        ])
      )[0].prompt_text
    ).toBe("What does “flower reuse” mean?");
  });

  it("keeps strict semantic validation after smart-quote recovery", () => {
    expect(() =>
      parseIntentJson(
        '[{“prompt_text”:“donate wedding flowers”,“bucket”:“purchase”,“paraphrases”:[]}]'
      )
    ).toThrow("invalid bucket: purchase");
  });

  it("rejects smart-quote input when the normalized retry is still malformed", () => {
    expect(() =>
      parseIntentJson('[{“prompt_text”:“donate wedding flowers”,“bucket”}]')
    ).toThrow("Intent JSON is invalid.");
  });

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

  it("versions slugs around existing and incoming collisions", () => {
    expect(
      buildIntentImportRows(
        "client-1",
        [
          { prompt_text: "Best Budgeting App" },
          { prompt_text: "Best Budgeting App!" },
          { prompt_text: "best budgeting app" },
        ],
        new Set(["best_budgeting_app_v1", "best_budgeting_app_v2"])
      ).map((row) => row.slug)
    ).toEqual([
      "best_budgeting_app_v3",
      "best_budgeting_app_v4",
      "best_budgeting_app_v5",
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

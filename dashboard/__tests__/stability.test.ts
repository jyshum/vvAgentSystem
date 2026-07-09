import { describe, expect, it } from "vitest";
import { aggregatePromptScores, computePromptStability } from "@/lib/stability";

describe("intent stability", () => {
  it("groups prompt score history by query_id and keeps the latest canonical label", () => {
    const runs = [
      { id: "run-1", ran_at: "2026-07-01T00:00:00Z" },
      { id: "run-2", ran_at: "2026-07-08T00:00:00Z" },
    ];
    const scores = [
      {
        run_id: "run-1",
        query_id: "intent-1",
        query: "best daycare software",
        llm: "chatgpt",
        mention_rate: 0.25,
        avg_mention_level: 2,
      },
      {
        run_id: "run-2",
        query_id: "intent-1",
        query: "top childcare management tools",
        llm: "chatgpt",
        mention_rate: 0.75,
        avg_mention_level: 3,
      },
    ];

    const stability = computePromptStability(aggregatePromptScores(scores, runs));

    expect(stability).toHaveLength(1);
    expect(stability[0].query_id).toBe("intent-1");
    expect(stability[0].query).toBe("top childcare management tools");
    expect(stability[0].trend.map((p) => p.mention_rate)).toEqual([0.25, 0.75]);
  });
});

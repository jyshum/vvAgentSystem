import { describe, expect, it } from "vitest";
import { clientTabs } from "@/lib/client-tabs";

describe("clientTabs", () => {
  it("omits the legacy Pages route from primary navigation", () => {
    const tabs = clientTabs("client-1");
    expect(tabs.map((tab) => tab.label)).toEqual([
      "OVERVIEW",
      "QUERIES",
      "RUNS",
      "CARDS",
      "CONFIG",
      "REPORTS",
    ]);
    expect(tabs.some((tab) => tab.href.endsWith("/pages"))).toBe(false);
  });
});

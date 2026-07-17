import { describe, expect, it } from "vitest";
import {
  GENERIC_NA_SUMMARY,
  GENERIC_UNKNOWN_SUMMARY,
  checkTitle,
  findingTitle,
  humanizeCheckId,
} from "@/lib/technical-audit-labels";

describe("technical-audit-labels", () => {
  it("maps known check ids to curated names", () => {
    expect(checkTitle("performance.crux")).toBe("Field performance (CrUX)");
    expect(checkTitle("integration.bing")).toBe("Bing sitemap submission");
  });

  it("falls back to a humanized id for unmapped checks", () => {
    expect(checkTitle("future.new_check")).toBe(humanizeCheckId("future.new_check"));
    expect(humanizeCheckId("future.new_check")).toBe("Future New Check");
  });

  it("uses the check name only when the summary is the generic placeholder", () => {
    // Generic unknown summary -> resolve to the check's real name.
    expect(findingTitle("performance.crux", GENERIC_UNKNOWN_SUMMARY)).toBe(
      "Field performance (CrUX)",
    );
    // Generic not-applicable summary -> also resolves to the check name.
    expect(findingTitle("links.internal_health", GENERIC_NA_SUMMARY)).toBe(
      "Internal link health",
    );
    // A real outcome summary is kept verbatim.
    expect(findingTitle("links.internal_health", "Internal links redirect or look like soft 404s")).toBe(
      "Internal links redirect or look like soft 404s",
    );
  });

  it("returns a safe label when the check id is missing", () => {
    expect(checkTitle(undefined)).toBe("Check");
  });
});

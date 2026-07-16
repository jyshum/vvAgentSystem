import { describe, expect, it } from "vitest";

import { clientTabs } from "@/lib/client-tabs";

describe("clientTabs", () => {
  it("includes an AUDIT tab", () => {
    const labels = clientTabs("client-1").map((tab) => tab.label);
    expect(labels).toContain("AUDIT");
  });

  it("no longer includes the retired CARDS tab", () => {
    const labels = clientTabs("client-1").map((tab) => tab.label);
    expect(labels).not.toContain("CARDS");
  });

  it("points AUDIT at the client's audit route", () => {
    const audit = clientTabs("client-1").find((tab) => tab.label === "AUDIT");
    expect(audit?.href).toBe("/admin/clients/client-1/audit");
  });
});

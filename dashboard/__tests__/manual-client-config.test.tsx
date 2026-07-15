// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";

import { ConfigForm } from "@/components/admin/ConfigForm";

afterEach(cleanup);

it("shows site platform and no scheduler controls", () => {
  render(<ConfigForm client={{
    id: "c1", name: "Christian", brand_name: "BudgetYourMD",
    website_domain: "budgetyourmd.ca", brand_variations: [], target_queries: [],
    competitors: [], gsc_site_url: "https://www.budgetyourmd.ca/",
    site_platform: "squarespace", implementation_mode: "copy_paste",
    created_at: "2026-07-15T00:00:00Z",
  }} />);
  expect((screen.getByLabelText("Site platform") as HTMLSelectElement).value).toBe("squarespace");
  expect(screen.queryByText("Pipeline Schedule")).toBeNull();
  expect(screen.queryByText("Frequency")).toBeNull();
});

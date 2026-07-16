// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LifecycleStrip } from "@/components/audit/LifecycleStrip";

afterEach(cleanup);

describe("LifecycleStrip", () => {
  it("renders non-zero lifecycle counts with regressed first", () => {
    render(
      <LifecycleStrip
        counts={{ regressed: 2, new: 3, resolved: 5, continuing: 40 }}
        previousRunAt="2026-07-09T11:02:00Z"
      />,
    );

    expect(screen.getByText("2 regressed")).toBeDefined();
    expect(screen.getByText("3 new")).toBeDefined();
    expect(screen.getByText("5 resolved")).toBeDefined();

    const items = screen.getAllByTestId("lifecycle-item");
    expect(items[0].textContent).toContain("regressed");
  });

  it("omits states with a zero count", () => {
    render(<LifecycleStrip counts={{ new: 1 }} previousRunAt="2026-07-09T11:02:00Z" />);
    expect(screen.queryByText(/regressed/)).toBeNull();
  });

  it("renders nothing when there is no previous run to compare against", () => {
    const { container } = render(
      <LifecycleStrip counts={{ new: 5 }} previousRunAt={null} />,
    );
    expect(container.firstChild).toBeNull();
  });
});

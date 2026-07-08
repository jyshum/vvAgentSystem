// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

describe("component test infra", () => {
  it("renders JSX into jsdom", () => {
    render(<div data-testid="ok">hello</div>);
    expect(screen.getByTestId("ok").textContent).toBe("hello");
  });
});

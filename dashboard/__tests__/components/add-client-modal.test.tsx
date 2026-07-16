// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

import { AddClientModal } from "@/components/admin/AddClientModal";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("AddClientModal intent validation", () => {
  it("shows invalid JSON directly beneath the textarea, marks it red, and focuses it", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { container } = render(<AddClientModal onClose={vi.fn()} />);
    fireEvent.change(screen.getByPlaceholderText("ChildSpot"), {
      target: { value: "Repeat Floral" },
    });
    fireEvent.change(screen.getByPlaceholderText("childspotapp.com"), {
      target: { value: "repeatfloral.org" },
    });

    const intentTextarea = container.querySelector("textarea");
    expect(intentTextarea).not.toBeNull();
    fireEvent.change(intentTextarea!, { target: { value: "[{not json}]" } });
    fireEvent.click(screen.getByRole("button", { name: "CREATE CLIENT" }));

    const inlineError = intentTextarea!.nextElementSibling;
    expect(inlineError?.textContent).toBe("Intent JSON is invalid.");
    expect(intentTextarea!.style.borderColor).toBe("var(--neg)");
    expect(intentTextarea!.getAttribute("aria-invalid")).toBe("true");
    expect(document.activeElement).toBe(intentTextarea);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

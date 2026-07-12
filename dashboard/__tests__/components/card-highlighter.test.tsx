// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { CardHighlighter } from "@/components/approvals/CardHighlighter";

function setSearch(search: string) {
  window.history.replaceState({}, "", `/admin/approvals${search}`);
}

describe("CardHighlighter", () => {
  afterEach(() => {
    cleanup();
    setSearch("");
  });

  it("scrolls to and highlights cards matching ?query=", () => {
    setSearch("?query=q-1");
    const scrollSpy = vi.fn();
    Element.prototype.scrollIntoView = scrollSpy;

    render(
      <div>
        <div data-query-id="q-1" data-testid="target" />
        <div data-query-id="q-2" data-testid="other" />
        <CardHighlighter />
      </div>
    );

    const target = document.querySelector<HTMLElement>('[data-testid="target"]')!;
    const other = document.querySelector<HTMLElement>('[data-testid="other"]')!;
    expect(scrollSpy).toHaveBeenCalledOnce();
    expect(target.style.backgroundColor).not.toBe("");
    expect(other.style.backgroundColor).toBe("");
  });

  it("does nothing without a query param", () => {
    setSearch("");
    const scrollSpy = vi.fn();
    Element.prototype.scrollIntoView = scrollSpy;

    render(
      <div>
        <div data-query-id="q-1" data-testid="target" />
        <CardHighlighter />
      </div>
    );

    expect(scrollSpy).not.toHaveBeenCalled();
  });
});

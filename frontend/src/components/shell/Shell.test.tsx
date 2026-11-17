import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import SectionDock from "./SectionDock";
import { revealCards } from "./AppStage";

describe("SectionDock", () => {
  afterEach(() => document.body.removeAttribute("data-section-dock"));

  it("moves the portal menu into the bottom capsule and keeps its handlers", () => {
    const onPick = vi.fn();
    const { container, unmount } = render(
      <div className="contents">
        <SectionDock label="Korxona boshqaruv menyusi">
          <div>Rekruting &amp; Qabul</div>
          <button type="button" className="fb-nav-item fb-nav-active" onClick={onPick}>
            Nomzodlar Kanbani
          </button>
        </SectionDock>
      </div>
    );
    const dock = screen.getByRole("navigation", { name: "Korxona boshqaruv menyusi" });
    expect(dock.parentElement).toBe(document.body);
    expect(container.contains(dock)).toBe(false);
    expect(dock.className).toContain("fb-section-dock");
    expect(document.body.hasAttribute("data-section-dock")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Nomzodlar Kanbani" }));
    expect(onPick).toHaveBeenCalledTimes(1);
    unmount();
    expect(document.body.hasAttribute("data-section-dock")).toBe(false);
  });
});

describe("revealCards", () => {
  it("animates only outermost visible cards, staggered", () => {
    const root = document.createElement("div");
    root.innerHTML = '<section class="skeuo-card"><div class="skeuo-card"></div></section><div class="fb-ink-card"></div><p></p>';
    document.body.appendChild(root);
    const calls: Array<{ el: Element; delay: number }> = [];
    root.querySelectorAll<HTMLElement>("*").forEach((el) => {
      el.getBoundingClientRect = () => ({ top: 10, bottom: 100, width: 100, height: 90, left: 0, right: 100, x: 0, y: 10, toJSON: () => ({}) });
      el.animate = ((_k: Keyframe[], o: KeyframeAnimationOptions) => {
        calls.push({ el, delay: Number(o.delay) });
        return {} as Animation;
      }) as HTMLElement["animate"];
    });
    root.animate = (() => ({}) as Animation) as HTMLElement["animate"];
    expect(revealCards(root)).toBe(2);
    expect(calls.map((c) => c.el.tagName)).toEqual(["SECTION", "DIV"]);
    expect(calls[1].delay).toBeGreaterThan(calls[0].delay);
    root.remove();
  });

  it("does nothing when the visitor prefers reduced motion", () => {
    const original = window.matchMedia;
    window.matchMedia = ((q: string) => ({ matches: q.includes("reduce") }) as MediaQueryList) as typeof window.matchMedia;
    const root = document.createElement("div");
    root.innerHTML = '<div class="skeuo-card"></div>';
    root.animate = (() => ({}) as Animation) as HTMLElement["animate"];
    expect(revealCards(root)).toBe(0);
    window.matchMedia = original;
  });
});

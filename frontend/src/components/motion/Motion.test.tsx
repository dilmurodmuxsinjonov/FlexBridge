import { act, fireEvent, render, screen } from "@testing-library/react";
import { useRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import CountUp from "./CountUp";
import InteractionLayer, { canPaintInside, watchBusy } from "./InteractionLayer";
import { useGlider } from "@/lib/motion";
import { ThemeProvider, revealOrigin, useSkeuoTheme } from "@/components/ThemeProvider";

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("CountUp", () => {
  it("shows the real value immediately when motion is reduced (jsdom has no matchMedia)", () => {
    const { rerender } = render(<CountUp value={35} />);
    expect(screen.getByText("35")).toBeInTheDocument();
    rerender(<CountUp value={70} />);
    expect(screen.getByText("70")).toBeInTheDocument();
  });
});

describe("watchBusy", () => {
  afterEach(() => vi.useRealTimers());

  it("marks a clicked button busy while it is disabled, then settles", async () => {
    const button = document.createElement("button");
    document.body.appendChild(button);
    watchBusy(button);
    button.disabled = true;
    await flush();
    expect(button.classList.contains("fb-busy")).toBe(true);
    expect(button.getAttribute("aria-busy")).toBe("true");
    button.disabled = false;
    await flush();
    expect(button.classList.contains("fb-busy")).toBe(false);
    expect(button.hasAttribute("aria-busy")).toBe(false);
    button.remove();
  });

  it("is attached by the global layer on click", async () => {
    function Form() {
      return (
        <button
          type="button"
          onClick={(e) => {
            const el = e.currentTarget;
            setTimeout(() => (el.disabled = true), 0);
          }}
        >
          Yuborish
        </button>
      );
    }
    render(
      <>
        <InteractionLayer />
        <Form />
      </>
    );
    const button = screen.getByRole("button", { name: "Yuborish" });
    fireEvent.click(button);
    await flush();
    await flush();
    expect(button).toHaveAttribute("aria-busy", "true");
  });

  it("only paints ripples inside clipped, positioned buttons with a free ::before", () => {
    const plain = document.createElement("button");
    document.body.appendChild(plain);
    expect(canPaintInside(plain)).toBe(false);
    plain.style.overflow = "hidden";
    plain.style.position = "relative";
    expect(canPaintInside(plain)).toBe(true);
    plain.remove();
  });
});

describe("useGlider", () => {
  it("tracks the active item and enables the slide after first placement", async () => {
    function Menu({ active }: { active: number }) {
      const box = useRef<HTMLElement>(null);
      const glider = useRef<HTMLSpanElement>(null);
      useGlider(box, glider);
      return (
        <nav ref={box} aria-label="Bo‘limlar">
          <span ref={glider} data-testid="glider" />
          {[0, 1].map((i) => (
            <button key={i} type="button" className={`fb-nav-item ${i === active ? "fb-nav-active" : ""}`}>
              {`Bo‘lim ${i}`}
            </button>
          ))}
        </nav>
      );
    }
    const { rerender } = render(<Menu active={0} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 40));
    });
    expect(screen.getByTestId("glider").style.opacity).toBe("1");
    expect(screen.getByRole("navigation")).toHaveAttribute("data-glider", "on");
    rerender(<Menu active={-1} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 40));
    });
    expect(screen.getByTestId("glider").style.opacity).toBe("0");
  });
});

describe("theme switch", () => {
  it("falls back to an instant switch without the View Transitions API", () => {
    function Toggle() {
      const { theme, toggleTheme } = useSkeuoTheme();
      return (
        <button type="button" onClick={toggleTheme}>
          {theme}
        </button>
      );
    }
    render(
      <ThemeProvider>
        <Toggle />
      </ThemeProvider>
    );
    fireEvent.click(screen.getByRole("button"));
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    fireEvent.click(screen.getByRole("button"));
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("grows the reveal from the pointer, or the button centre for keyboard presses", () => {
    expect(revealOrigin({ clientX: 120, clientY: 30 })).toEqual({ x: 120, y: 30 });
    const button = document.createElement("button");
    button.getBoundingClientRect = () => ({ left: 10, top: 20, width: 40, height: 40, right: 50, bottom: 60, x: 10, y: 20, toJSON: () => ({}) });
    expect(revealOrigin({ clientX: 0, clientY: 0, currentTarget: button })).toEqual({ x: 30, y: 40 });
  });
});

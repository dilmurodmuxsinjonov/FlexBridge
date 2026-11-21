import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import LiquidBackdropCanvas from "./LiquidBackdropCanvas";
import LiquidGlass3D from "./LiquidGlass3D";
import LiquidGlassEngine from "./LiquidGlassEngine";
import GooFilter from "@/components/motion/GooFilter";

describe("Optical Liquid Glass components", () => {
  afterEach(() => {
    delete document.documentElement.dataset.liquidGlass;
  });

  it("falls back cleanly to fresnel mode in jsdom without errors", () => {
    render(<LiquidGlassEngine />);
    expect(document.documentElement.dataset.liquidGlass).toBe("fresnel");
  });

  it("mounts #fb-goo SVG filter with prismatic rim dispersion primitives", () => {
    const { container } = render(<GooFilter />);
    const filter = container.querySelector("#fb-goo");
    expect(filter).not.toBeNull();
    expect(container.querySelectorAll("feOffset").length).toBeGreaterThanOrEqual(3);
    expect(container.querySelector("feSpecularLighting")).not.toBeNull();
  });

  it("renders accessible aria-hidden backdrop canvas and degrades safely without WebGL2", () => {
    const { unmount } = render(<LiquidBackdropCanvas />);
    const canvas = screen.getByTestId("liquid-backdrop");
    expect(canvas).toHaveAttribute("aria-hidden", "true");
    expect(canvas.style.pointerEvents).toBe("none");
    unmount();
  });

  it("renders LiquidGlass3D showcase with graceful fallback when WebGL2 is unavailable", () => {
    const { container, unmount } = render(<LiquidGlass3D label="3D optik shisha" />);
    expect(screen.getByText("3D optik shisha")).toBeInTheDocument();
    expect(container.querySelector("[aria-hidden='true']")).not.toBeNull();
    unmount();
  });
});

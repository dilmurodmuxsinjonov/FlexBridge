"use client";

import React, { createContext, useContext, useEffect, useSyncExternalStore } from "react";

export type SkeuoTheme = "light" | "dark";

interface ThemeContextValue {
  theme: SkeuoTheme;
  setTheme: (next: SkeuoTheme) => void;
  /** Pass the click event to grow the new theme out of the pressed button. */
  toggleTheme: (origin?: ThemeOrigin) => void;
}

export interface ThemeOrigin {
  clientX?: number;
  clientY?: number;
  currentTarget?: EventTarget | null;
}

type ViewTransitionDocument = Document & {
  startViewTransition?: (update: () => void) => { ready: Promise<void>; finished: Promise<void> };
};

/** Circle centre for the reveal: the pointer, or the button centre for keyboard presses. */
export function revealOrigin(origin?: ThemeOrigin): { x: number; y: number } {
  const x = origin?.clientX ?? 0;
  const y = origin?.clientY ?? 0;
  if ((x || y) || !(origin?.currentTarget instanceof Element)) {
    return { x: x || window.innerWidth - 48, y: y || 40 };
  }
  const box = origin.currentTarget.getBoundingClientRect();
  return { x: box.left + box.width / 2, y: box.top + box.height / 2 };
}

const STORAGE_KEY = "flexbridge:theme";
const THEME_EVENT = "flexbridge:theme-change";

const ThemeContext = createContext<ThemeContextValue>({
  theme: "light",
  setTheme: () => undefined,
  toggleTheme: () => undefined,
});

function applyDomTheme(next: SkeuoTheme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (next === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
  root.dataset.theme = next;
}

function getThemeSnapshot(): SkeuoTheme {
  if (typeof window === "undefined") return "light";
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

function getServerSnapshot(): SkeuoTheme {
  return "light";
}

function subscribeTheme(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  const handler = () => onStoreChange();
  window.addEventListener("storage", handler);
  window.addEventListener(THEME_EVENT, handler);
  return () => {
    window.removeEventListener("storage", handler);
    window.removeEventListener(THEME_EVENT, handler);
  };
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useSyncExternalStore(subscribeTheme, getThemeSnapshot, getServerSnapshot);

  useEffect(() => {
    applyDomTheme(theme);
  }, [theme]);

  const setTheme = (next: SkeuoTheme) => {
    applyDomTheme(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Ignore storage write failures in strict environments
    }
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event(THEME_EVENT));
    }
  };

  const toggleTheme = (origin?: ThemeOrigin) => {
    const next: SkeuoTheme = theme === "light" ? "dark" : "light";
    const doc = document as ViewTransitionDocument;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (typeof doc.startViewTransition !== "function" || reduce) {
      setTheme(next);
      return;
    }
    // The new theme grows as a circle out of the pressed button (View Transitions API).
    const { x, y } = revealOrigin(origin);
    const radius = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));
    const transition = doc.startViewTransition(() => setTheme(next));
    transition.ready
      .then(() => {
        document.documentElement.animate(
          { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
          { duration: 560, easing: "cubic-bezier(0.2, 0.8, 0.2, 1)", pseudoElement: "::view-transition-new(root)" }
        );
      })
      .catch(() => undefined);
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useSkeuoTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}

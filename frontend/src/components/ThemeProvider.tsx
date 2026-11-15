"use client";

import React, { createContext, useContext, useEffect, useSyncExternalStore } from "react";

export type SkeuoTheme = "light" | "dark";

interface ThemeContextValue {
  theme: SkeuoTheme;
  setTheme: (next: SkeuoTheme) => void;
  toggleTheme: () => void;
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

  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
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

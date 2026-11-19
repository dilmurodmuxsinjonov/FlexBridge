import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  // `fetchAuthMe()` keeps a short client cache; the auth-changed event drops
  // it so one test's session answer never leaks into the next test.
  // Node-environment tests (e.g. session.test.ts) have no `window`.
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("flexbridge:auth-changed"));
  }
});

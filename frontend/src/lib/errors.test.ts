import { describe, expect, it } from "vitest";
import { describeRequestError, SIGN_IN_REQUIRED_MESSAGE } from "./errors";

describe("describeRequestError", () => {
  it("maps 401 to the sign-in message", () => {
    const err = Object.assign(new Error("UNAUTHORIZED"), { status: 401 });
    expect(describeRequestError(err, "fallback")).toBe(SIGN_IN_REQUIRED_MESSAGE);
  });

  it("uses the error message for other failures", () => {
    const err = Object.assign(new Error("Server band"), { status: 503 });
    expect(describeRequestError(err, "fallback")).toBe("Server band");
  });

  it("falls back for empty or non-Error values", () => {
    expect(describeRequestError(new Error(""), "fallback")).toBe("fallback");
    expect(describeRequestError("oops", "fallback")).toBe("fallback");
    expect(describeRequestError(null, "fallback")).toBe("fallback");
  });
});

describe("describeLoginError", () => {
  it("maps known codes and hides unknown machine codes", async () => {
    const { describeLoginError } = await import("./errors");
    expect(describeLoginError("INVALID_CREDENTIALS")).toMatch(/parol noto‘g‘ri/);
    expect(describeLoginError("RATE_LIMITED")).toMatch(/Juda ko‘p urinish/);
    expect(describeLoginError("SOMETHING_NEW")).not.toContain("SOMETHING_NEW");
    expect(describeLoginError("Ushbu kirish sahifasi faqat Talaba hisoblari uchun.")).toBe(
      "Ushbu kirish sahifasi faqat Talaba hisoblari uchun."
    );
    expect(describeLoginError("Failed to fetch")).toMatch(/Server bilan bog‘lanib/);
  });
});

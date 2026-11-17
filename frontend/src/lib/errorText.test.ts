import { describe, expect, it } from "vitest";
import { errorText, humanizeMessage } from "./errorText";
import { enumLabel } from "./labels";

describe("errorText", () => {
  it("never renders [object Object] when the BFF forwards the backend detail object", () => {
    const text = errorText({ error: { code: "INSTITUTIONS_NOT_FOUND", message: "x" } }, "SUPERVISIONS_FETCH_FAILED");
    expect(text).toBe("Universitet topilmadi yoki siz uning xodimi emassiz.");
    expect(text).not.toContain("object");
  });

  it("maps a raw code string and hides unknown codes behind a generic sentence", () => {
    expect(errorText({ error: "RATE_LIMITED" }, "X_FAILED")).toMatch(/Juda ko‘p urinish/);
    expect(errorText({ error: "SOMETHING_ODD" }, "AGREEMENTS_FETCH_FAILED")).not.toMatch(/[A-Z]{3,}_/);
    expect(errorText({ detail: { code: "PLACEMENT_NOT_FOUND" } }, "Yuklab bo‘lmadi.")).toBe("Ma’lumot topilmadi.");
  });

  it("explains validation conflicts found in the staging run instead of asking to retry", () => {
    expect(errorText({ ok: false, error: { code: "TIMETABLE_SLOT_OVERLAP" } }, "TIMETABLE_SAVE_FAILED")).toMatch(/shu vaqtda boshqa dars bor/);
    expect(errorText({ error: "APPLICATION_ALREADY_EXISTS", message: "Active application exists" }, "APPLY_FAILED")).toMatch(/allaqachon ariza/);
    expect(errorText({ error: "SHIFT_OVERLAP" }, "X_FAILED")).toMatch(/to‘qnashadi/);
  });

  it("keeps a human message and a human fallback", () => {
    expect(errorText({ message: "Parol noto‘g‘ri." }, "LOGIN_FAILED")).toBe("Parol noto‘g‘ri.");
    expect(errorText({}, "Shartnomalarni yuklab bo‘lmadi.")).toBe("Shartnomalarni yuklab bo‘lmadi.");
    expect(errorText(null, "TIMETABLE_FETCH_FAILED")).not.toContain("TIMETABLE");
  });

  it("humanizes messages that were already thrown", () => {
    expect(humanizeMessage("[object Object]")).not.toContain("object");
    expect(humanizeMessage("ORG_SCOPE_FORBIDDEN")).toBe("Bu bo‘lim faqat korxona xodimlariga ochiq.");
    expect(humanizeMessage("Oddiy matn")).toBe("Oddiy matn");
  });
});

describe("enumLabel", () => {
  it("translates known enums and softens unknown codes", () => {
    expect(enumLabel("INTERNSHIP_AGREEMENT")).toBe("Amaliyot shartnomasi");
    expect(enumLabel("HYBRID")).toBe("Gibrid");
    expect(enumLabel("OWNER")).toBe("Asosiy egasi");
    expect(enumLabel("SOME_NEW_VALUE")).toBe("Some new value");
    expect(enumLabel(null, "Gibrid")).toBe("Gibrid");
    expect(enumLabel("Toshkent")).toBe("Toshkent");
  });
});

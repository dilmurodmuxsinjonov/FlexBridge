import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  fetchAuthOptions: vi.fn().mockResolvedValue({ telegram_mode: "DISABLED" }),
  fetchAuthChallengeStatus: vi.fn(),
  sendTelegramBotUpdate: vi.fn(),
}));

const rec = vi.hoisted(() => ({
  startRecovery: vi.fn(),
  verifyRecoveryCode: vi.fn(),
  requestRecovery: vi.fn(),
  completeRecovery: vi.fn(),
  fetchRecoveryStatus: vi.fn(),
}));
vi.mock("@/lib/recovery", async (importOriginal) => ({ ...(await importOriginal<typeof import("@/lib/recovery")>()), ...rec }));

import PasswordRecovery from "./PasswordRecovery";
import { RecoveryError, normalizeRecoveryDestination } from "@/lib/recovery";

async function reachFactorStep() {
  rec.startRecovery.mockResolvedValue({ challenge_id: "c-1", delivery_method: "SMS", expires_in: 300, resend_after: 60 });
  rec.verifyRecoveryCode.mockResolvedValue({ verification_token: "v".repeat(40) });
  render(<PasswordRecovery />);
  fireEvent.change(screen.getByLabelText("Telefon raqam yoki elektron pochta"), { target: { value: "90 123 45 67" } });
  fireEvent.click(screen.getByRole("button", { name: /Kod olish/ }));
  const otp = await screen.findByLabelText("6 xonali kod");
  fireEvent.change(otp, { target: { value: "654321" } });
  await screen.findByLabelText("Ilovadagi 6 xonali kod");
}

describe("PasswordRecovery", () => {
  beforeEach(() => vi.clearAllMocks());

  it("resets the password with OTP + authenticator code", async () => {
    await reachFactorStep();
    expect(rec.startRecovery).toHaveBeenCalledWith("PHONE", "+998901234567", "SMS");
    expect(rec.verifyRecoveryCode).toHaveBeenCalledWith("c-1", "654321");

    rec.requestRecovery.mockResolvedValue({ recovery_id: "r-1", recovery_token: "s", status: "READY_TO_RESET", reset_token: "t", expires_in: 1800 });
    fireEvent.change(screen.getByLabelText("Ilovadagi 6 xonali kod"), { target: { value: "111222" } });
    fireEvent.click(screen.getByRole("button", { name: /Davom etish/ }));
    expect(await screen.findByLabelText("Yangi parol")).toBeInTheDocument();
    expect(rec.requestRecovery).toHaveBeenCalledWith("v".repeat(40), { totp_code: "111222" });

    const save = screen.getByRole("button", { name: /Parolni saqlash/ });
    fireEvent.change(screen.getByLabelText("Yangi parol"), { target: { value: "short1" } });
    expect(save).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Yangi parol"), { target: { value: "yangi-parol-2026" } });
    fireEvent.change(screen.getByLabelText("Parolni takrorlang"), { target: { value: "yangi-parol-2026" } });
    rec.completeRecovery.mockResolvedValue({ status: "COMPLETED", reauthentication_required: true });
    fireEvent.click(save);
    expect(await screen.findByText("Parol yangilandi")).toBeInTheDocument();
    expect(rec.completeRecovery).toHaveBeenCalledWith("r-1", "t", "yangi-parol-2026");
  });

  it("queues manual review when the user has no second factor", async () => {
    await reachFactorStep();
    rec.requestRecovery.mockResolvedValue({ recovery_id: "r-2", recovery_token: "s", status: "PENDING_REVIEW", expires_in: 1800 });
    fireEvent.click(screen.getByRole("button", { name: /Qo‘lda tekshiruvga yuborish/ }));
    expect(await screen.findByText("So‘rov qabul qilindi")).toBeInTheDocument();
    expect(await screen.findByText("r-2")).toBeInTheDocument();
    expect(rec.requestRecovery).toHaveBeenCalledWith("v".repeat(40), {});
  });

  it("shows a readable message for a wrong code", async () => {
    rec.startRecovery.mockResolvedValue({ challenge_id: "c-1", delivery_method: "EMAIL", expires_in: 300, resend_after: 60 });
    rec.verifyRecoveryCode.mockRejectedValue(new RecoveryError("INVALID_OR_EXPIRED_CODE", 401));
    render(<PasswordRecovery />);
    fireEvent.change(screen.getByLabelText("Telefon raqam yoki elektron pochta"), { target: { value: "Ali@Misol.uz" } });
    fireEvent.click(screen.getByRole("button", { name: /Kod olish/ }));
    fireEvent.change(await screen.findByLabelText("6 xonali kod"), { target: { value: "000000" } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Kod noto‘g‘ri yoki muddati o‘tgan");
    expect(rec.startRecovery).toHaveBeenCalledWith("EMAIL", "Ali@Misol.uz", "EMAIL");
  });
});

describe("normalizeRecoveryDestination", () => {
  it("normalizes Uzbek phone formats and keeps e-mail", () => {
    expect(normalizeRecoveryDestination("+998 (90) 123-45-67")).toEqual({ channel: "PHONE", destination: "+998901234567" });
    expect(normalizeRecoveryDestination("998901234567")).toEqual({ channel: "PHONE", destination: "+998901234567" });
    expect(normalizeRecoveryDestination("901234567")).toEqual({ channel: "PHONE", destination: "+998901234567" });
    expect(normalizeRecoveryDestination(" a@b.uz ")).toEqual({ channel: "EMAIL", destination: "a@b.uz" });
  });
});

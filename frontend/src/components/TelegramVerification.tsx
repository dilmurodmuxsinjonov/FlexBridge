"use client";

import { useState } from "react";
import { CheckCircle2, ExternalLink, Loader2, Send, Smartphone } from "lucide-react";
import { sendTelegramBotUpdate } from "@/lib/api";

export type TelegramMode = "LIVE" | "SIMULATION" | "DISABLED";

export interface TelegramVerificationProps {
  /** From GET /auth/options. Unknown values are treated as LIVE (never simulate by default). */
  mode: TelegramMode;
  challengeId: string;
  /** Phone number entered on the website; Telegram must share the same number. */
  phone: string;
  botUsername: string;
  deepLink: string | null;
  /** True once the challenge status reports telegram_verified (the page polls it). */
  verified: boolean;
  displayName?: string;
  /** SIMULATION only: called with the echoed code so the page can prefill it. */
  onSimulatedCode?: (code: string) => void;
}

/**
 * Phone confirmation through the FlexBridge Telegram bot.
 *
 * LIVE: the user opens the bot from the deep link, presses Start and shares their
 * own contact with Telegram's native button; the bot replies with the 6-digit
 * code. The website never sees or forges Telegram messages.
 * SIMULATION (local staging only): the old in-page bot emulator, clearly labelled.
 */
export default function TelegramVerification(props: TelegramVerificationProps) {
  const { mode, botUsername, deepLink, verified, phone } = props;

  return (
    <div className="p-4 rounded-2xl skeuo-well space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-600 dark:text-sky-400 shrink-0">
            <Send className="w-4 h-4" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <div className="text-xs font-semibold text-[var(--fb-ink)] truncate">@{botUsername}</div>
            <div className="text-[11px] text-[var(--fb-ink-muted)]">Rasmiy FlexBridge boti</div>
          </div>
        </div>
        <span
          role="status"
          className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border shrink-0 ${
            verified
              ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30"
              : "bg-amber-500/15 text-amber-800 dark:text-amber-300 border-amber-500/30"
          }`}
        >
          {verified ? "Raqam tasdiqlandi" : "Telegramdan javob kutilmoqda"}
        </span>
      </div>

      {mode === "SIMULATION" ? (
        <SimulatedBot {...props} />
      ) : (
        <ol className="space-y-2 text-xs text-[var(--fb-ink-secondary)] list-none">
          <li className="flex gap-2">
            <StepNo n={1} />
            <div className="flex-1 space-y-2">
              <p>Telegram ilovasida botni oching.</p>
              {deepLink && (
                <a
                  href={deepLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full skeuo-btn-obsidian text-xs font-semibold"
                >
                  <span>Telegramda ochish</span>
                  <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
                </a>
              )}
            </div>
          </li>
          <li className="flex gap-2">
            <StepNo n={2} />
            <p className="flex-1">
              Botda <strong className="text-[var(--fb-ink)]">«Start»</strong> tugmasini bosing.
            </p>
          </li>
          <li className="flex gap-2">
            <StepNo n={3} />
            <p className="flex-1">
              <strong className="text-[var(--fb-ink)]">«📱 Telefon raqamni yuborish»</strong> tugmasini bosing. Telegram
              hisobingiz raqami <strong className="font-mono text-[var(--fb-ink)]">{phone}</strong> bilan bir xil
              bo‘lishi kerak.
            </p>
          </li>
          <li className="flex gap-2">
            <StepNo n={4} />
            <p className="flex-1">Bot yuborgan 6 xonali kodni pastdagi maydonga kiriting.</p>
          </li>
        </ol>
      )}
    </div>
  );
}

function StepNo({ n }: { n: number }) {
  return (
    <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-[var(--fb-well-deep)] text-[11px] font-bold text-[var(--fb-ink)] flex items-center justify-center">
      {n}
    </span>
  );
}

function SimulatedBot({ challengeId, phone, displayName, verified, onSimulatedCode }: TelegramVerificationProps) {
  const [telegramUserId] = useState(() => Math.floor(100000000 + Math.random() * 899999999));
  const [started, setStarted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [contactPhone, setContactPhone] = useState(phone);

  const send = async (extra: Record<string, unknown>) => {
    setBusy(true);
    setError(null);
    try {
      const res = await sendTelegramBotUpdate({
        challenge_id: challengeId,
        message: {
          from: { id: telegramUserId, first_name: displayName || "Sinov" },
          chat: { id: telegramUserId, type: "private" },
          ...extra,
        },
      });
      setMessage(res.bot_message ?? null);
      if (res.otp_code) onSimulatedCode?.(res.otp_code);
      return true;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sinov botida xatolik.");
      return false;
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-2.5">
      <p className="text-[11px] font-semibold text-amber-800 dark:text-amber-300">
        Sinov rejimi: haqiqiy Telegram bot ulanmagan. Bu panel faqat lokal staging uchun.
      </p>
      {!started ? (
        <button
          type="button"
          disabled={busy}
          onClick={async () => setStarted(await send({ text: `/start ${challengeId}` }))}
          className="w-full py-2 rounded-xl skeuo-btn-secondary text-xs font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          <span>Botni ishga tushirish (/start)</span>
        </button>
      ) : verified ? (
        <p className="flex items-center gap-1.5 text-xs text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 className="w-4 h-4" /> Kod maydonga qo‘yildi.
        </p>
      ) : (
        <div className="flex gap-2">
          <label htmlFor="sim-contact" className="sr-only">Telegram raqami</label>
          <input
            id="sim-contact"
            type="tel"
            value={contactPhone}
            onChange={(e) => setContactPhone(e.target.value)}
            className="flex-1 px-3 py-2 rounded-xl skeuo-input text-xs font-mono"
          />
          <button
            type="button"
            disabled={busy || !contactPhone.trim()}
            onClick={() =>
              send({ contact: { phone_number: contactPhone.trim(), first_name: displayName || "Sinov", user_id: telegramUserId } })
            }
            className="px-3 py-2 rounded-xl skeuo-btn-obsidian text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
          >
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Smartphone className="w-3.5 h-3.5" />}
            <span>Kontaktni yuborish</span>
          </button>
        </div>
      )}
      {message && <p className="text-[11px] text-[var(--fb-ink-secondary)] whitespace-pre-line">{message}</p>}
      {error && (
        <p role="alert" className="text-[11px] text-rose-700 dark:text-rose-300">
          {error}
        </p>
      )}
    </div>
  );
}

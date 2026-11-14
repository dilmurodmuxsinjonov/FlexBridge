"use client";

import { useState } from "react";
import { Lock, Mail, KeyRound, AlertCircle, Loader2, X, ShieldCheck } from "lucide-react";
import { loginUser, verifyMfa, AuthUser } from "@/lib/api";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: AuthUser) => void;
  title?: string;
  subtitle?: string;
}

export default function AuthModal({
  isOpen,
  onClose,
  onSuccess,
  title = "Tizimga kirish",
  subtitle = "Hisobingiz orqali FlexBridge xizmatlaridan foydalaning",
}: AuthModalProps) {
  const [destination, setDestination] = useState("");
  const [password, setPassword] = useState("");
  const [mfaTicket, setMfaTicket] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage(null);

    try {
      if (mfaTicket) {
        // MFA Verification step
        const result = await verifyMfa(mfaTicket, mfaCode);
        if (result.ok && !result.mfa_required) {
          onSuccess({
            user_id: result.user_id,
            session_id: "active",
            roles: result.roles,
          });
          onClose();
        } else if (!result.ok) {
          setErrorMessage(result.error);
        }
      } else {
        // Initial Login step
        const result = await loginUser(destination.trim(), password);
        if (result.ok) {
          if (result.mfa_required) {
            setMfaTicket(result.mfa_ticket);
          } else {
            onSuccess({
              user_id: result.user_id,
              session_id: "active",
              roles: result.roles,
            });
            onClose();
          }
        } else {
          setErrorMessage(result.error);
        }
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Xatolik yuz berdi");
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setMfaTicket(null);
    setMfaCode("");
    setErrorMessage(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-md bg-surface-card border border-white/[0.1] rounded-xl shadow-2xl p-6 sm:p-8 flex flex-col gap-5">
        <button
          onClick={onClose}
          type="button"
          aria-label="Yopish"
          className="absolute top-4 right-4 p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/[0.06] transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex flex-col gap-1.5 text-center sm:text-left">
          <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary mb-1">
            <Lock className="w-5 h-5" />
          </div>
          <h2 className="text-xl font-heading font-bold text-white tracking-tight">{title}</h2>
          <p className="text-xs text-zinc-400">{subtitle}</p>
        </div>

        {errorMessage && (
          <div className="flex items-start gap-2.5 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {!mfaTicket ? (
            <>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-zinc-300">
                  Email yoki Telefon raqam
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-zinc-400">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={destination}
                    onChange={(e) => setDestination(e.target.value)}
                    placeholder="user@example.com yoki +998901234567"
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-colors"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-zinc-300">Parol</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-zinc-400">
                    <KeyRound className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-colors"
                  />
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-col gap-3">
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 shrink-0" />
                <span>2-bosqichli tasdiqlash: Authenticator ilovangizdagi 6 xonali kodni kiriting.</span>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-zinc-300">MFA / TOTP Kod</label>
                <input
                  type="text"
                  required
                  pattern="^[0-9]{6}$"
                  maxLength={6}
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  placeholder="123456"
                  className="w-full text-center tracking-widest text-lg font-mono py-2 rounded-lg bg-surface border border-white/[0.08] text-white focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-colors"
                />
              </div>
              <button
                type="button"
                onClick={handleReset}
                className="text-xs text-zinc-400 hover:text-white underline text-left"
              >
                ← Boshqa hisob bilan kirish
              </button>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-2 py-2.5 px-4 rounded-lg bg-primary hover:bg-primary/90 text-white font-medium text-xs md:text-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-primary/20"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Tekshirilmoqda...</span>
              </>
            ) : mfaTicket ? (
              <span>Tasdiqlash va Kirish</span>
            ) : (
              <span>Kirish</span>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

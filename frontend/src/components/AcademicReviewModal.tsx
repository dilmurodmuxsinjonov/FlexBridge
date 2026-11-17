"use client";

import { useEffect, useState } from "react";
import {
  X,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Calendar,
  Clock,
  FileText,
  UserCheck,
  Check,
  RotateCcw,
  Briefcase,
  Layers,
} from "lucide-react";
import {
  fetchAcademicLogRevision,
  submitAcademicLogReview,
  AcademicLogRevisionDetail,
} from "@/lib/api";

interface AcademicReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  revisionId: string | null;
  studentName?: string;
  onSuccess: () => void;
}

export default function AcademicReviewModal({
  isOpen,
  onClose,
  revisionId,
  studentName = "Talaba",
  onSuccess,
}: AcademicReviewModalProps) {
  const [detail, setDetail] = useState<AcademicLogRevisionDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [decision, setDecision] = useState<"REVIEWED" | "NEEDS_REVISION">("REVIEWED");
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  useEffect(() => {
    let ignore = false;
    if (isOpen && revisionId) {
      fetchAcademicLogRevision(revisionId)
        .then((data) => {
          if (!ignore) {
            setDetail(data);
            setIsLoading(false);
          }
        })
        .catch((err: unknown) => {
          if (!ignore) {
            setLoadError(err instanceof Error ? err.message : "Kundalik tafsilotlarini yuklashda xatolik");
            setIsLoading(false);
          }
        });
    }

    return () => {
      ignore = true;
    };
  }, [isOpen, revisionId]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!revisionId) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await submitAcademicLogReview(revisionId, {
        decision,
        comment: comment.trim(),
      });
      setSubmitSuccess(true);
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1200);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "Baholash qarorini yuborishda xatolik yuz berdi");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl max-h-[90vh] bg-surface-card border border-white/[0.1] rounded-xl shadow-2xl flex flex-col overflow-hidden">
        {/* HEADER */}
        <div className="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between bg-surface/50">
          <div className="flex flex-col gap-0.5">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                Akademik Baholash
              </span>
              {detail && (
                <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-zinc-300">
                  Rev #{detail.revision}
                </span>
              )}
            </div>
            <h2 className="text-base font-heading font-bold text-white">
              {studentName} amaliyot kundaligi
            </h2>
          </div>

          <button
            onClick={onClose}
            type="button"
            aria-label="Yopish"
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/[0.06] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* BODY */}
        <div className="p-6 overflow-y-auto flex flex-col gap-5 text-xs text-zinc-300">
          {isLoading && (
            <div className="py-16 flex flex-col items-center justify-center gap-3 text-zinc-400">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span>Kundalik ma’lumotlari yuklanmoqda...</span>
            </div>
          )}

          {loadError && (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{loadError}</span>
            </div>
          )}

          {submitSuccess && (
            <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2.5">
              <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-400" />
              <div className="flex flex-col">
                <span className="font-semibold">Kundalik muvaffaqiyatli baholandi!</span>
                <span className="text-zinc-400">Qaror qabul qilindi va navbat yangilanmoqda...</span>
              </div>
            </div>
          )}

          {detail && !isLoading && (
            <>
              {/* KEY STATS BAR */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="p-3 rounded-lg bg-surface border border-white/[0.06] flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 text-zinc-400">
                    <Calendar className="w-3.5 h-3.5" />
                    <span className="text-[11px]">Sana</span>
                  </div>
                  <span className="font-mono font-medium text-white">{detail.local_date}</span>
                </div>

                <div className="p-3 rounded-lg bg-surface border border-white/[0.06] flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 text-zinc-400">
                    <Clock className="w-3.5 h-3.5" />
                    <span className="text-[11px]">Sarflangan vaqt</span>
                  </div>
                  <span className="font-mono font-medium text-white">
                    {detail.total_minutes} daqiqa ({(detail.total_minutes / 60).toFixed(1)} soat)
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-surface border border-white/[0.06] flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 text-zinc-400">
                    <Layers className="w-3.5 h-3.5" />
                    <span className="text-[11px]">Kun turi</span>
                  </div>
                  <span className="font-medium text-white capitalize">{detail.day_type}</span>
                </div>

                <div className="p-3 rounded-lg bg-surface border border-white/[0.06] flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 text-zinc-400">
                    <Briefcase className="w-3.5 h-3.5" />
                    <span className="text-[11px]">Yo‘nalish</span>
                  </div>
                  <span className="font-medium text-white truncate" title={detail.purpose}>
                    {detail.purpose}
                  </span>
                </div>
              </div>

              {/* SUMMARY SECTION */}
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-1.5 text-zinc-400">
                  <FileText className="w-3.5 h-3.5 text-primary" />
                  <span className="font-semibold text-zinc-200">Kundalik hisoboti xulosasi:</span>
                </div>
                <div className="p-3.5 rounded-lg bg-surface/70 border border-white/[0.06] text-zinc-200 leading-relaxed text-xs">
                  {detail.summary || "Xulosa kiritilmagan."}
                </div>
              </div>

              {/* TASKS LIST */}
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between text-zinc-400">
                  <span className="font-semibold text-zinc-200">
                    Bajarilgan vazifalar ({detail.tasks.length} ta):
                  </span>
                </div>
                {detail.tasks.length === 0 ? (
                  <div className="p-3 rounded-lg bg-surface/40 border border-white/[0.04] text-zinc-400 italic">
                    Ushbu kunga alohida topshiriqlar biriktirilmagan.
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    {detail.tasks.map((task, idx) => (
                      <div
                        key={task.id}
                        className="p-3 rounded-lg bg-surface border border-white/[0.06] flex flex-col gap-1.5"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium text-white text-xs">
                            {idx + 1}. {task.title || task.code || "Amaliy topshiriq"}
                          </span>
                          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-white/[0.06] text-zinc-300">
                            {task.minutes} min
                          </span>
                        </div>
                        <p className="text-zinc-300 leading-relaxed text-xs">
                          {task.result_text}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* WORKPLACE REVIEWS (MENTOR) */}
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-1.5 text-zinc-400">
                  <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="font-semibold text-zinc-200">Ish joyi (Mentor) xulosasi:</span>
                </div>
                {detail.workplace_reviews && detail.workplace_reviews.length > 0 ? (
                  <div className="flex flex-col gap-2">
                    {detail.workplace_reviews.map((rev) => (
                      <div
                        key={rev.id}
                        className="p-3 rounded-lg bg-surface border border-white/[0.06] flex flex-col gap-1"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                              rev.decision === "REVIEWED"
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                            }`}
                          >
                            {rev.decision === "REVIEWED" ? "Mentor tomonidan tasdiqlangan" : "Qayta ishlashga qaytarilgan"}
                          </span>
                          <span className="font-mono text-[10px] text-zinc-400">
                            {new Date(rev.decided_at).toLocaleString("uz-UZ")}
                          </span>
                        </div>
                        {rev.comment && <p className="text-zinc-300 text-xs mt-1">{rev.comment}</p>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-3 rounded-lg bg-surface/40 border border-white/[0.04] text-zinc-400 italic">
                    Ish joyi rahbari (mentor) tomonidan hali xulosa qoldirilmagan.
                  </div>
                )}
              </div>

              {/* EVALUATION FORM */}
              <form onSubmit={handleSubmit} className="mt-2 pt-4 border-t border-white/[0.08] flex flex-col gap-4">
                <div className="flex flex-col gap-2">
                  <label className="font-semibold text-zinc-200 text-xs">
                    Akademik qaroringizni tanlang:
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setDecision("REVIEWED")}
                      className={`p-3 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                        decision === "REVIEWED"
                          ? "bg-emerald-500/15 border-emerald-500/50 text-emerald-300 shadow-md shadow-emerald-500/10"
                          : "bg-surface border-white/[0.08] text-zinc-400 hover:bg-surface-high hover:text-white"
                      }`}
                    >
                      <Check className="w-4 h-4" />
                      <span>Tasdiqlash (Qabul qilish)</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setDecision("NEEDS_REVISION")}
                      className={`p-3 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                        decision === "NEEDS_REVISION"
                          ? "bg-amber-500/15 border-amber-500/50 text-amber-300 shadow-md shadow-amber-500/10"
                          : "bg-surface border-white/[0.08] text-zinc-400 hover:bg-surface-high hover:text-white"
                      }`}
                    >
                      <RotateCcw className="w-4 h-4" />
                      <span>Qaytarish (Qayta ishlashga)</span>
                    </button>
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <label className="font-semibold text-zinc-200 text-xs">
                      O‘qituvchi xulosasi va ko‘rsatmalari (Izoh):
                    </label>
                    <span className="text-[10px] text-zinc-400">{comment.length} / 10000</span>
                  </div>
                  <textarea
                    rows={3}
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    maxLength={10000}
                    placeholder="Talabaga ushbu amaliyot kuni bo‘yicha tavsiya, e'tiroz yoki ko‘rsatmalaringizni yozing..."
                    className="w-full px-3.5 py-2.5 rounded-lg bg-surface border border-white/[0.1] text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-primary/60 focus:ring-1 focus:ring-primary/40 resize-none"
                  />
                </div>

                {submitError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
                    <span>{submitError}</span>
                  </div>
                )}

                <div className="flex items-center justify-end gap-2.5 pt-2">
                  <button
                    type="button"
                    onClick={onClose}
                    disabled={isSubmitting}
                    className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-medium text-zinc-300 transition-colors"
                  >
                    Bekor qilish
                  </button>

                  <button
                    type="submit"
                    disabled={isSubmitting || submitSuccess}
                    className="px-5 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-2 shadow-lg shadow-primary/20 disabled:opacity-50"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Yuborilmoqda...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Qarorni tasdiqlash</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

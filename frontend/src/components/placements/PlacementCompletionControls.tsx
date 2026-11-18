"use client";

import React, { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Flag,
  Loader2,
  XCircle,
} from "lucide-react";
import {
  exportPlacementReport,
  fetchFileDownloadUrl,
  submitCompletionRequest,
  type PlacementExportResult,
} from "@/lib/placementLifecycle";
import { enumLabel } from "@/lib/labels";

export default function PlacementCompletionControls({
  placementId,
  status,
  termsId,
  version,
  onUpdated,
}: {
  placementId: string;
  status: string;
  termsId: string;
  version: number;
  onUpdated: () => void;
}) {
  const [reason, setReason] = useState("");
  const [earlyReason, setEarlyReason] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [exportReceipt, setExportReceipt] = useState<PlacementExportResult | null>(null);

  const runCompletion = async (
    decision: "REQUEST_COMPLETION" | "CONFIRM_COMPLETION" | "REJECT_COMPLETION"
  ) => {
    setBusy(decision);
    setError(null);
    setNotice(null);
    try {
      const res = await submitCompletionRequest(placementId, {
        terms_id: termsId,
        version,
        decision,
        reason: reason.trim() || undefined,
        early_reason: earlyReason.trim() || undefined,
      });
      const nextStatus = res.placement_status || res.status || "";
      setNotice(
        `Qaror qayd etildi: ${enumLabel(decision)}${nextStatus ? ` (Holat: ${enumLabel(nextStatus)})` : ""}`
      );
      onUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Yakunlash so‘rovida xatolik yuz berdi.");
    } finally {
      setBusy(null);
    }
  };

  const runExport = async (format: "PDF" | "JSON") => {
    setBusy(`EXPORT_${format}`);
    setError(null);
    try {
      const receipt = await exportPlacementReport(placementId, format, true);
      setExportReceipt(receipt);
      setNotice(`${format} amaliyot hisoboti tayyorlandi.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Hisobot eksport qilinmadi.");
    } finally {
      setBusy(null);
    }
  };

  const handleDownloadFile = async (fileId: string) => {
    setBusy("DOWNLOAD");
    try {
      const res = await fetchFileDownloadUrl(fileId);
      const href = res.signed_url || res.url;
      if (href && /^https?:\/\//i.test(href)) {
        window.open(href, "_blank", "noopener,noreferrer");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Yuklab olish havolasi olinmadi.");
    } finally {
      setBusy(null);
    }
  };

  const canComplete = status === "ACTIVE" || status === "COMPLETION_REQUESTED";

  return (
    <div className="space-y-4">
      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-700 dark:text-rose-300"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {notice && (
        <div className="flex items-start gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-800 dark:text-emerald-300">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{notice}</span>
        </div>
      )}

      {/* Two-sided completion sign-off (API-049) */}
      <div className="rounded-2xl skeuo-well p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h4 className="text-xs font-bold text-[var(--fb-ink)]">
            Amaliyotni yakunlash (ikki tomonlama tasdiq)
          </h4>
          <span className="rounded-full skeuo-badge-recessed px-2.5 py-0.5 text-[11px] font-semibold">
            {enumLabel(status)}
          </span>
        </div>

        {canComplete ? (
          <>
            <div className="grid gap-2.5 sm:grid-cols-2">
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Yakunlash izohi (ixtiyoriy)..."
                className="skeuo-input rounded-xl px-3 py-2 text-xs"
              />
              <input
                type="text"
                value={earlyReason}
                onChange={(e) => setEarlyReason(e.target.value)}
                placeholder="Muddatidan oldin yakunlash sababi (agar soat yetmasa)..."
                className="skeuo-input rounded-xl px-3 py-2 text-xs"
              />
            </div>

            <div className="flex flex-wrap gap-2">
              {status === "ACTIVE" && (
                <button
                  type="button"
                  disabled={Boolean(busy)}
                  onClick={() => void runCompletion("REQUEST_COMPLETION")}
                  className="skeuo-btn-obsidian inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold disabled:opacity-50"
                >
                  {busy === "REQUEST_COMPLETION" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Flag className="h-3.5 w-3.5" />
                  )}
                  Yakunlashni so‘rash
                </button>
              )}
              {status === "COMPLETION_REQUESTED" && (
                <>
                  <button
                    type="button"
                    disabled={Boolean(busy)}
                    onClick={() => void runCompletion("CONFIRM_COMPLETION")}
                    className="skeuo-btn-obsidian inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold disabled:opacity-50"
                  >
                    {busy === "CONFIRM_COMPLETION" ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-3.5 w-3.5" />
                    )}
                    Yakunlashni tasdiqlash
                  </button>
                  <button
                    type="button"
                    disabled={Boolean(busy)}
                    onClick={() => void runCompletion("REJECT_COMPLETION")}
                    className="skeuo-btn-secondary inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold disabled:opacity-50"
                  >
                    {busy === "REJECT_COMPLETION" ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <XCircle className="h-3.5 w-3.5 text-rose-500" />
                    )}
                    Yakunlashni rad etish
                  </button>
                </>
              )}
            </div>
          </>
        ) : (
          <p className="text-xs text-[var(--fb-ink-muted)]">
            Yakunlash harakatlari faqat «{enumLabel("ACTIVE")}» yoki «{enumLabel("COMPLETION_REQUESTED")}» holatida mavjud.
          </p>
        )}
      </div>

      {/* Placement Report Export (API-052) */}
      <div className="rounded-2xl skeuo-well p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h4 className="text-xs font-bold text-[var(--fb-ink)]">
              Shaxsiy amaliyot hisoboti eksporti
            </h4>
            <p className="text-[11px] text-[var(--fb-ink-muted)]">
              Tasdiqlangan kundaliklar, soatlar yig‘indisi va sharhlar jamlanmasi.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={Boolean(busy)}
              onClick={() => void runExport("PDF")}
              className="skeuo-btn-secondary inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold disabled:opacity-50"
            >
              {busy === "EXPORT_PDF" ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Download className="h-3.5 w-3.5" />
              )}
              PDF eksport
            </button>
            <button
              type="button"
              disabled={Boolean(busy)}
              onClick={() => void runExport("JSON")}
              className="skeuo-btn-secondary inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold disabled:opacity-50"
            >
              {busy === "EXPORT_JSON" ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <FileSpreadsheet className="h-3.5 w-3.5" />
              )}
              JSON eksport
            </button>
          </div>
        </div>

        {exportReceipt && (
          <div className="rounded-xl border border-[var(--fb-border)] p-3 text-xs space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono font-semibold text-[var(--fb-ink)]">
                Eksport #{exportReceipt.export_id.slice(0, 8)} · {exportReceipt.export_format}
              </span>
              <button
                type="button"
                disabled={busy === "DOWNLOAD"}
                onClick={() => void handleDownloadFile(exportReceipt.file_id)}
                className="skeuo-btn-obsidian inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-semibold"
              >
                <Download className="h-3 w-3" /> Yuklab olish
              </button>
            </div>
            <p className="text-[11px] text-[var(--fb-ink-muted)]">{exportReceipt.disclaimer}</p>
          </div>
        )}
      </div>
    </div>
  );
}

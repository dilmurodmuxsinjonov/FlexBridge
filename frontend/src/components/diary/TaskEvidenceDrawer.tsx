"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileUp,
  Loader2,
  Paperclip,
  X,
} from "lucide-react";
import { enumLabel } from "@/lib/labels";
import {
  attachLogEntryEvidence,
  fetchFileDownloadUrl,
  fetchLogEntryEvidence,
  type LogEvidenceItem,
} from "@/lib/placementLifecycle";
import { errorText } from "@/lib/errorText";

type VisibilityOption = "HOST_AND_ACADEMIC" | "HOST_ONLY" | "ACADEMIC_ONLY";

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Faylni o‘qib bo‘lmadi."));
    reader.onload = () => {
      const result = String(reader.result || "");
      const idx = result.indexOf(",");
      resolve(idx >= 0 ? result.slice(idx + 1) : result);
    };
    reader.readAsDataURL(file);
  });
}

export default function TaskEvidenceDrawer({
  isOpen,
  entryId,
  taskTitle,
  locked,
  onClose,
  onAttached,
}: {
  isOpen: boolean;
  entryId: string | null;
  taskTitle: string;
  locked: boolean;
  onClose: () => void;
  onAttached: () => void;
}) {
  const [items, setItems] = useState<LogEvidenceItem[]>([]);
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const [visibility, setVisibility] = useState<VisibilityOption>("HOST_AND_ACADEMIC");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const targetKey = isOpen && entryId ? `${entryId}:${refreshTick}` : null;
  const loading = Boolean(targetKey && loadedKey !== targetKey);

  const reloadEvidence = useCallback(() => {
    setRefreshTick((t) => t + 1);
  }, []);

  useEffect(() => {
    if (!targetKey || !entryId) return;
    let active = true;
    fetchLogEntryEvidence(entryId)
      .then((rows) => {
        if (!active) return;
        setItems(rows);
        setError(null);
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Dalillar ro‘yxatini yuklab bo‘lmadi.");
        }
      })
      .finally(() => {
        if (active) setLoadedKey(targetKey);
      });
    return () => {
      active = false;
    };
  }, [targetKey, entryId]);

  if (!isOpen || !entryId) return null;

  const handleUploadAndAttach = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Biriktirish uchun PDF fayl tanlang.");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const contentBase64 = await fileToBase64(selectedFile);
      const upRes = await fetch("/api/bff/candidate/files/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          filename: selectedFile.name,
          purpose: "PORTFOLIO",
          content_base64: contentBase64,
        }),
      });
      const upData = await upRes.json().catch(() => ({}));
      if (!upRes.ok || upData?.ok === false) {
        throw new Error(errorText(upData, "FILE_UPLOAD_FAILED"));
      }
      const fileId = String(upData.file_id || upData.id || upData.file?.id || "");
      if (!fileId) {
        throw new Error("Yuklangan fayl identifikatori qaytmadi.");
      }

      await attachLogEntryEvidence(entryId, fileId, visibility);
      setSelectedFile(null);
      setNotice("Dalil vazifaga muvaffaqiyatli biriktirildi (API-055).");
      reloadEvidence();
      onAttached();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Dalil biriktirishda xatolik yuz berdi.");
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = async (fileId: string) => {
    setError(null);
    try {
      const res = await fetchFileDownloadUrl(fileId);
      const href = res.signed_url || res.url;
      if (href && /^https?:\/\//i.test(href)) {
        window.open(href, "_blank", "noopener,noreferrer");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Fayl havolasi olinmadi.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-[var(--fb-border)] bg-[var(--fb-surface)] text-[var(--fb-ink)] shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between gap-3 border-b border-[var(--fb-border)] px-5 py-4">
          <div className="min-w-0">
            <h2 className="text-sm font-bold flex items-center gap-1.5">
              <Paperclip className="w-4 h-4 text-[var(--fb-accent)]" />
              <span>Vazifa dalillari (`API-055`)</span>
            </h2>
            <p className="text-xs text-[var(--fb-ink-muted)] truncate mt-0.5">{taskTitle || "Kundalik vazifasi"}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Yopish"
            className="rounded-lg p-1.5 hover:bg-black/5 dark:hover:bg-white/10"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/25 text-xs text-rose-500 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
          {notice && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-xs text-emerald-500 flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{notice}</span>
            </div>
          )}

          {!locked ? (
            <form onSubmit={handleUploadAndAttach} className="p-3.5 rounded-xl border border-[var(--fb-border)] space-y-3">
              <label className="flex flex-col gap-1">
                <span className="text-xs font-semibold">Ko‘rinish darajasi</span>
                <select
                  value={visibility}
                  onChange={(e) => setVisibility(e.target.value as VisibilityOption)}
                  className="skeuo-input rounded-xl px-3 py-2 text-xs"
                >
                  <option value="HOST_AND_ACADEMIC">{enumLabel("HOST_AND_ACADEMIC")}</option>
                  <option value="HOST_ONLY">{enumLabel("HOST_ONLY")}</option>
                  <option value="ACADEMIC_ONLY">{enumLabel("ACADEMIC_ONLY")}</option>
                </select>
              </label>

              <label className="flex flex-col gap-1">
                <span className="text-xs font-semibold">PDF fayl tanlash</span>
                <input
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="text-xs"
                />
              </label>

              <button
                type="submit"
                disabled={busy || !selectedFile}
                className="skeuo-btn-accent px-4 py-2 text-xs font-semibold inline-flex items-center gap-1.5 disabled:opacity-50"
              >
                {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileUp className="w-3.5 h-3.5" />}
                <span>Yuklash va biriktirish</span>
              </button>
            </form>
          ) : (
            <p className="text-xs text-[var(--fb-ink-muted)]">
              Yozuv yuborilganligi sababli yangi dalil qo‘shib bo‘lmaydi (faqat ko‘rish rejimi).
            </p>
          )}

          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-[var(--fb-ink-secondary)]">
              Biriktirilgan fayllar ({items.length})
            </h3>
            {loading ? (
              <div className="py-4 flex items-center gap-2 text-xs text-[var(--fb-ink-muted)]">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Yuklanmoqda...
              </div>
            ) : items.length === 0 ? (
              <p className="text-xs text-[var(--fb-ink-muted)]">Hozircha dalil biriktirilmagan.</p>
            ) : (
              items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between gap-2 p-2.5 rounded-xl border border-[var(--fb-border)] text-xs"
                >
                  <div className="min-w-0">
                    <div className="font-medium truncate">{item.filename || item.file_id}</div>
                    <div className="text-[11px] text-[var(--fb-ink-muted)]">{enumLabel(item.visibility)}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleDownload(item.file_id)}
                    className="px-2.5 py-1 rounded-lg border border-[var(--fb-border)] text-[11px] font-semibold inline-flex items-center gap-1 hover:bg-black/5 dark:hover:bg-white/5"
                  >
                    <Download className="w-3 h-3" /> Yuklab olish
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import { AlertCircle, FileUp, Loader2, Upload, X } from "lucide-react";
import {
  resubmitCandidateEnrollmentVerification,
  uploadCandidatePdfFile,
  type CandidateEnrollmentItem,
} from "@/lib/api";

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Faylni o‘qib bo‘lmadi."));
    reader.onload = () => {
      const s = String(reader.result || "");
      const idx = s.indexOf(",");
      resolve(idx >= 0 ? s.slice(idx + 1) : s);
    };
    reader.readAsDataURL(file);
  });
}

export default function EnrollmentResubmitModal({
  enrollment,
  onClose,
  onSaved,
}: {
  enrollment: CandidateEnrollmentItem | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [program, setProgram] = useState(enrollment?.program || "");
  const [startDate, setStartDate] = useState(enrollment?.start_date || "");
  const [endDate, setEndDate] = useState(enrollment?.end_date || "");
  const [evidenceNote, setEvidenceNote] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!enrollment) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Kamida bitta tasdiqlovchi PDF hujjat tanlang.");
      return;
    }
    if (evidenceNote.trim().length < 15) {
      setError("Izoh kamida 15 ta belgidan iborat bo‘lishi kerak.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const content_base64 = await toBase64(selectedFile);
      const uploaded = await uploadCandidatePdfFile({
        filename: selectedFile.name,
        purpose: "CERTIFICATE",
        content_base64,
      });
      await resubmitCandidateEnrollmentVerification(enrollment.id, {
        expected_revision: Math.max(1, Number(enrollment.revision || 1)),
        program: program.trim() || enrollment.program,
        start_date: startDate || enrollment.start_date,
        end_date: endDate || null,
        file_ids: [uploaded.file_id],
        evidence_note: evidenceNote.trim(),
      });
      onSaved();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Qayta topshirishda xatolik yuz berdi.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-[#121214] border border-white/[0.1] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 text-xs text-white">
        <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
          <h3 className="text-sm font-bold flex items-center gap-2">
            <Upload className="w-4 h-4 text-blue-400" />
            <span>Talabalik hujjatini qayta yuborish</span>
          </h3>
          <button type="button" onClick={onClose} aria-label="Yopish" className="text-zinc-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div role="alert" className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          <label className="flex flex-col gap-1">
            <span className="text-zinc-300 font-semibold">Yo‘nalish / Dastur *</span>
            <input
              type="text"
              required
              value={program}
              onChange={(e) => setProgram(e.target.value)}
              className="px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white"
            />
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="flex flex-col gap-1">
              <span className="text-zinc-300 font-semibold">Boshlangan sana</span>
              <input
                type="date"
                required
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-zinc-300 font-semibold">Tugash sanasi</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white"
              />
            </label>
          </div>
          <label className="flex flex-col gap-1">
            <span className="text-zinc-300 font-semibold">Yangi PDF dalil (ma’lumotnoma/buyruq) *</span>
            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="text-zinc-300"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-zinc-300 font-semibold">Izoh (kamida 15 belgi) *</span>
            <textarea
              rows={3}
              required
              value={evidenceNote}
              onChange={(e) => setEvidenceNote(e.target.value)}
              placeholder="Masalan: OTM dekanati tomonidan yangilangan ma’lumotnoma ilova qilindi."
              className="px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white"
            />
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-3 py-2 rounded-lg bg-white/[0.06] text-zinc-300">
              Bekor qilish
            </button>
            <button
              type="submit"
              disabled={busy}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold inline-flex items-center gap-1.5 disabled:opacity-50"
            >
              {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileUp className="w-3.5 h-3.5" />}
              <span>Qayta yuborish</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

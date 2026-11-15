# FlexBridge 1.4 — Frontend & Server-Side BFF (`frontend/`)

Ushbu papka faqat **Next.js 16.4.6 (App Router)**, **TypeScript** va **Tailwind CSS** asosidagi frontend hamda Server-Side BFF (Backend-For-Frontend) kodlarini o‘z ichiga oladi.

---

## 1. Ichki Tuzilma (`frontend/src/`)

- `src/app/` — Sahifalar va Server-Side BFF API route-lar (jami 72 ta route):
  - `api/auth/` — Sessiya boshqaruvi (`login`, `logout`, `me`, `mfa/verify`).
  - `api/bff/` — Himoyalangan BFF proxy qatlami (`auth`, `candidate`, `employer`, `university`, `operator`, `opportunities`, `public`, `me`).
  - `nomzod/` — Nomzod portali (Profil, Ko‘nikmalar, Jadval, HEMIS Talabalik, Portfolio, Sertifikatlar & PDF Rezyume, Arizalar, Shartnomalar, Kundalik, Baholar, Saqlanganlar, Bildirishnomalar, Xavfsizlik, Yordam).
  - `employer/` — Ish beruvchi portali (Kanban voronka, Nomzodlar aqlli qidiruvi, Mentor kundalik tekshiruvi, Tashkilot & Jamoa, Billing & Kvotalar).
  - `university/` — Universitet portali (Kundaliklar navbati, Biriktirilgan amaliyotlar & Xulosalar, Kafedra taqsimoti, Hisobotlar eksporti, 3 ustunli Analitika).
  - `operator/` — Platforma operatori SOC portali (Audit oqimi, Verifikatsiya, 4-ko‘z Break-Glass, Murojaatlar & DR SLA, Moliya & Solishtiruv).
  - `kirish/` va `royxatdan-otish/` — Mustaqil kirish (2FA bilan) va ro‘yxatdan o‘tish (SMS hamda Telegram Bot orqali telefon raqamni tasdiqlash bilan).
  - `shartlar/`, `maxfiylik/`, `haqida/` — Ommaviy yuridik va yordam CMS sahifalari.
- `src/components/` — Umumiy UI komponentlar (`Navbar.tsx`, `Footer.tsx`, `AuthModal.tsx`, `AcademicReviewModal.tsx`).
- `src/lib/` — TypeScript API SDK (`api.ts`) va server-side AES-256-GCM HttpOnly sessiya xavfsizligi (`server/session.ts`).

---

## 2. Ishga Tushirish va Tekshirish

```powershell
cd frontend
npm ci
npx tsc --noEmit
npm run lint
npm run build
```

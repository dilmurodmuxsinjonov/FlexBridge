# Frontend — arxitektura xaritasi

Next.js 16.4.6 (App Router), React 19.2, TypeScript, Tailwind CSS 3.4. Agentlar uchun qisqa qoidalar: [`frontend/AGENTS.md`](../../frontend/AGENTS.md).

## 1. So'rov yo'li

```
Brauzer ──► src/app/api/bff/** (Next.js server) ──► backend /api/v1/** (FastAPI)
              │  shifrlangan HttpOnly sessiya cookie (BFF_SESSION_SECRET)
              │  CSRF: verifyCsrfOrigin, UUID tekshiruvi
              └─ lib/server/{session,proxy,backendProxy}.ts
```

- `lib/server/session.ts` — sessiya cookie'ni shifrlash/ochish, `backendFetch`, `completeAuthenticatedSession`, `verifyCsrfOrigin`.
- `lib/server/proxy.ts` — `proxyAuthed(request, path, { method, body?, fallbackError })` (GET/POST/PATCH/DELETE; o'zgartiruvchi so'rovlarda CSRF avtomatik, sessiya bo'lmasa 401 `AUTH_REQUIRED`), `backendErrorCode`, `UUID_RE`.
- `lib/server/backendProxy.ts` — `proxyBackendJson`, fayl oqimi uchun `proxyBackendFileStream`.
- Muhit o'zgaruvchilari: `BACKEND_INTERNAL_URL`, `BFF_SESSION_SECRET` (bo'lmasa sessiyalar qayta ishga tushganda tugaydi), `COOKIE_SECURE`.

## 2. Portallar va sahifalar

| Portal | Yo'l | Asosiy fayllar |
| --- | --- | --- |
| Ommaviy katalog | `/`, `/ishlar/[id]`, `/haqida`, `/maxfiylik`, `/shartlar` | `app/page.tsx`, `app/ishlar/[id]/page.tsx` |
| Kirish | `/kirish`, `/royxatdan-otish`, `/parolni-tiklash`, `/talaba/*`, `/korxona/*`, `/universitet/*`, `/operator/kirish` | `components/auth/` |
| Talaba | `/nomzod` + `arizalar`, `saqlanganlar`, `shartnomalar`, `jadval`, `kundalik`, `baholar`, `bildirishnomalar`, `xavfsizlik`, `yordam` | `app/nomzod/layout.tsx` (bo'lim kapsulasi), `components/profile/`, `diary/`, `timetable/`, `resume/` |
| Korxona | `/employer` (tablar: KANBAN, SEARCH_HUB, MENTOR_HUB, ORG_HUB, BILLING_HUB) | `app/employer/page.tsx`, `components/employer/EmployerOverview.tsx` |
| Universitet | `/university` (queue, assignments, documents, coordinator, enrollments, timetable, exports, analytics, staff) | `app/university/page.tsx`, `components/university/` |
| Operator | `/operator` (AUDIT, VERIFICATION, MODERATION, BREAK_GLASS, SUPPORT_OPS, FINANCE — rolga qarab) | `app/operator/page.tsx`, `components/operator/` |
| Xabarlar | `/xabarlar` (shaxsiy va guruh chat) | `components/chat/`, `lib/chat.ts` |

Portal sahifalari ichki tablarni `flexbridge:dock-tab` hodisasi bilan qabul qiladi va `flexbridge:portal-tab-changed` bilan e'lon qiladi. Tizimga kirish/chiqish — `flexbridge:auth-changed`.

## 3. BFF guruhlari (`src/app/api/bff/`)

`auth`, `candidate`, `chat` (allowlist), `employer`, `files`, `internship-documents`, `invitations`, `me`, `operator` (shu jumladan `moderation/*`), `opportunities`, `placements`, `public`, `support-tickets`, `university`.

## 4. Umumiy yordamchilar (`src/lib/`)

| Fayl | Vazifa |
| --- | --- |
| `api.ts` | Brauzer SDK (BFF chaqiruvlari, turlar) |
| `roles.ts` | Rol → portal (`resolvePortalDashboard`), operator modullari (`canUseOperatorModule`) |
| `errorText.ts`, `labels.ts` | Xato kodlari va enum'larni o'zbekcha matnga |
| `person.ts` | `initials`, `firstName`, `uzDate`, `isoWeekday` |
| `useAsyncData.ts` | Kalit bo'yicha yuklash, `reload`/`mutate` |
| `motion.ts` | `prefersReducedMotion`, `useGlider` |
| `chat.ts`, `diary.ts`, `timetable.ts`, `moderation.ts`, `orgTeam.ts`, `universityStaff.ts`, `recovery.ts`, `resumeContract.ts` | Domen yordamchilari |

## 5. Dizayn va harakat

Qobiq, tokenlar, sinflar va animatsiya qoidalari: [`DIZAYN_VA_HARAKAT.md`](DIZAYN_VA_HARAKAT.md).

## 6. Tekshiruv

- Statik: `npm run lint`, `npx tsc --noEmit -p .`, `npm test`, `npm run build` (CI: `.github/workflows/frontend-build.yml`, qo'shimcha `npm audit --audit-level=high`).
- Brauzer: [`docs/operations/STAGING_VA_E2E.md`](../operations/STAGING_VA_E2E.md) va `scripts/e2e/`.

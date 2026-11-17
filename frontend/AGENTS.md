# Frontend bo'limi — agentlar uchun qoidalar

Ildizdagi `AGENTS.md` (muzlatilgan `main`, faqat integration branch, maxfiy ma'lumotlar qoidasi) bu yerda ham to'liq amal qiladi. Bu fayl faqat **frontend ishiga** xos qo'shimchalar.

## Egalik chegarasi

- Frontend vazifasi faqat `frontend/**`, `docs/frontend/**` va kerak bo'lsa `scripts/e2e/**` ga tegadi.
- `backend/**` ga tegmang. Backend javobida maydon yetishmasa: `backend/AGENTS.md` bo'yicha alohida backend vazifasi oching yoki BFF'da xavfsiz normalizatsiya qiling (masalan `lib/api.ts` dagi API-005 tashkilot nomi).
- API shakli o'zgaradigan ish ikki tomonlama: avval backend PR (test bilan), keyin frontend PR. Umumiy shartnoma: `contracts/r1_api_matrix.csv`.

## Tuzilma (qisqa)

| Yo'l | Nima |
| --- | --- |
| `src/app/<portal>/` | Sahifalar: `nomzod/` (talaba), `employer/`, `university/`, `operator/`, `xabarlar/`, ommaviy `/`, `ishlar/[id]`, `haqida/`, `maxfiylik/`, `shartlar/` |
| `src/app/{kirish,royxatdan-otish,parolni-tiklash}`, `talaba/`, `korxona/`, `universitet/`, `operator/kirish` | Kirish va ro'yxatdan o'tish sahifalari |
| `src/app/api/bff/**` | Server-side BFF: brauzer faqat shu yerga murojaat qiladi |
| `src/app/api/auth/**` | Sessiya (login, logout, me, mfa) |
| `src/components/` | UI: `shell/` (qurilma qobig'i), `motion/` (harakat), `skeuo/`, `profile/`, `employer/`, `university/`, `operator/`, `chat/`, `diary/`, `timetable/`, `resume/`, `auth/` |
| `src/lib/` | `api.ts` (SDK), `roles.ts`, `labels.ts`, `errorText.ts`, `person.ts`, `motion.ts`, `useAsyncData.ts`, domen yordamchilari; `server/` — sessiya va proksi |

Batafsil xarita: [`docs/frontend/README.md`](../docs/frontend/README.md). Dizayn va harakat qoidalari: [`docs/frontend/DIZAYN_VA_HARAKAT.md`](../docs/frontend/DIZAYN_VA_HARAKAT.md).

## Buyruqlar (CI bilan bir xil)

```powershell
cd frontend
npm ci
npm run lint        # eslint --max-warnings=0
npx tsc --noEmit -p .
npm test            # vitest run
npm run build
```

PR'dan oldin to'rttasi ham toza bo'lishi shart. UI o'zgarishi bo'lsa, brauzerda ham tekshiring: [`docs/operations/STAGING_VA_E2E.md`](../docs/operations/STAGING_VA_E2E.md).

## Majburiy qoidalar

1. **BFF**: yangi backend chaqiruvi `src/app/api/bff/**` route orqali, `proxyAuthed` / `proxyBackendJson` bilan. O'zgartiruvchi so'rovlarda CSRF (`verifyCsrfOrigin`) va UUID tekshiruvi (`UUID_RE`). Token brauzerga hech qachon chiqmaydi.
2. **Xatolar**: foydalanuvchiga xom kod (`*_FAILED`, UUID) ko'rsatilmaydi — `errorText()` va `enumLabel()` dan foydalaning, yangi kodlarni `lib/errorText.ts` / `lib/labels.ts` ga qo'shing.
3. **Rollar**: portal va modul ruxsatlari faqat `lib/roles.ts` dan (`resolvePortalDashboard`, `canUseOperatorModule`, `is*Roles`). Eski rol kodlarini qo'lda yozmang.
4. **Ranglar**: faqat `globals.css` tokenlari (`--fb-*`). Shaffoflik uchun `color-mix(in srgb, var(--x) NN%, transparent)` — `bg-[var(--x)]/NN` ishlamaydi.
5. **Modal va popover**: `createPortal(..., document.body)` bilan (blur/animatsiyali ota element `fixed` ni qamab qo'yadi). Bo'lim menyusi — `SectionDock`.
6. **React**: ma'lumot `useAsyncData(key, fetcher)` bilan; render paytida ref o'qilmaydi; effekt ichida sinxron `setState` o'rniga hosila qiymat yoki render-time moslash.
7. **Matn**: o'zbekcha, oddiy so'zlar bilan; texnik ID'lar ko'rsatilmaydi.
8. **Test**: yangi komponent/yordamchi uchun `*.test.ts(x)` (Vitest + Testing Library). jsdom'da `matchMedia` yo'q — `prefersReducedMotion()` `true` qaytaradi.

## Ish oxirida

- `docs/journals/01_AI_XOTIRASI_VA_QOIDALAR.md` («Joriy holat» + «Ish tarixi» oxiriga yozuv) va `03_BOSQICHLAR_VA_HOLAT.md` ga yozing.
- PR bazasi: `integration/r1-agent-collaboration`. Merge faqat exact-head CI yashil bo'lganda.

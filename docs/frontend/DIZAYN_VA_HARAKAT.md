# Dizayn tizimi va harakat qatlami

Manba: `frontend/src/app/globals.css` (tokenlar va sinflar), `src/components/shell/`, `src/components/motion/`, `src/components/glass/`, `src/lib/glassOptics.ts`, `src/lib/motion.ts`. Tarix: LOG-179 (monoxrom bento), LOG-188 («qurilma» qobig'i, #264), LOG-189 (harakat qatlami, #266), LOG-210 (haqiqiy optik suyuq shisha va WebGL2, #303).

## 1. Ranglar — faqat tokenlar

- Yorug'/qorong'i rejim `html.dark` sinfi bilan (`ThemeProvider`, kalit `localStorage["flexbridge:theme"]`).
- Asosiy tokenlar: `--fb-canvas`, `--fb-ink`, `--fb-ink-secondary`, `--fb-ink-muted`, `--fb-card-top/bottom`, `--fb-stage`, `--fb-well`, `--fb-well-deep`, `--fb-border`, `--fb-accent` (`#e0622d`), `--fb-accent-strong`, `--fb-focus`, `--fb-ink-card*`, `--fb-pill-active-*`, soyalar `--fb-shadow-*`.
- Yangi rang qo'shmang; shaffoflik uchun `color-mix(in srgb, var(--fb-…) NN%, transparent)`.
- To'q bloklar (`fb-ink-card`, `skeuo-obsidian`) ichidagi matn uchun `data-skeuo-dark="true"` qo'ying.

## 2. «Qurilma» qobig'i (har bir oyna)

| Qism | Komponent / sinf | Izoh |
| --- | --- | --- |
| Yuqori to'q kapsula | `Navbar.tsx` → `.fb-topbar`, `.fb-topbar-avatar`, `.fb-topbar-well`, `.fb-orb`, `.fb-topbar-chip` | Avatar + salom, holat maydoni, metall tugmalar |
| Chap rels (lg+) | `Navbar.tsx` → `.fb-rail`, `.fb-rail-btn[data-tip]`, `.fb-glider-knob` | Tezkor manzillar, mavzu, yuqoriga, chiqish |
| Ekran-panel | `shell/AppStage.tsx` → `.fb-stage-shell`, `.fb-slab`, `.fb-slab-sheen` | Burchak vintlari; **transform/filter ishlatilmaydi** (`fixed` bolalar buzilmasin) |
| Bo'lim kapsulasi | `shell/SectionDock.tsx` → `.fb-section-dock` | Portal menyusi `createPortal` bilan body'ga; tugmalar, rol tekshiruvi va hisoblagichlar sahifada qoladi; `body[data-section-dock]` umumiy dock'ni yashiradi |
| Mobil dock | `Navbar.tsx` → `.fb-main-dock` | Faqat bo'lim kapsulasi bo'lmagan sahifalarda |

Bento elementlari: `.fb-panel`, `.fb-ink-card`, `.fb-display`, `.fb-nav-item` (+`.fb-nav-active`/`.fb-nav-idle`), `.fb-capsule`, `.fb-bar` (silindr), `.fb-seg`, `.fb-avatar`, `.fb-progress`, `.fb-file-row`, `.fb-icon-btn`, `.fb-ring`.

## 3. Harakat qatlami

| Nima | Qayerda | Qanday ishlaydi |
| --- | --- | --- |
| Bosish chuqurligi | CSS `:active` / `.fb-pressed` | Har bir tugma bosilganda ~2–3% botadi; klaviatura Enter/Space ham |
| Ripple | `motion/InteractionLayer.tsx` → `.fb-ripple` | Bosilgan nuqtadan tugma rangida; faqat `::before` bo'sh va `overflow:hidden` tugmalarda |
| Band holat | `watchBusy` → `.fb-busy`, `.fb-busy-sheen`, `aria-busy`, `.fb-settle` | Bosilgan tugma `disabled` bo'lsa (so'rov ketyapti) — avtomatik; sahifa o'zgarishi shart emas |
| Suyuq pill/knob | `lib/motion.ts` → `useGlider` + `.fb-glider` | Faol band (`aria-current="page"`, `.fb-nav-active`, `data-active`) ostiga suyuqlik tomchisidek oqadi: to'rt chet alohida prujina (oldingi chet tez, orqadagisi kech), cho'zilganda ingichkalashadi, tezlik ≤ 21000 px/s, joyiga ~0.1–0.15 s da tushadi (LOG-195, 3x), og'ir render tugagach (≤ 30 ms) boshlanadi; matn rangi tomchi qoplagan bandga qarab (`data-under-glider`). Pozitsiya rAF'dan — CSS easing qo'shmang (LOG-191) |
| Tomchi izi | `motion/GooFilter.tsx` (`#fb-goo`) + `.fb-goo` qatlami + `.fb-drop` | Glider `.fb-goo` ichida bo'lsa: harakat boshida orqa chetdan 1 kichik tomchi uziladi va tez qaytadi, tez harakatda kam sonli mayda tomchilar to'kilib tez so'nadi (LOG-193 da yumshatilgan); filtr yaqin shakllarni suyuq bo'yin bilan qo'shadi va soyani chizadi (LOG-192) |
| Suyuq shisha (glider) | `#fb-goo` filtri | Pill/tomchi/rels tugmasi: 18% shaffof shisha tana, o'tkir `feSpecularLighting` (`surfaceScale="5.2"`, `specularConstant="1.05"`, `specularExponent="42"`), 42% Fresnel yorug' chet va niqoblangan iliq-kehribo/soviq-moviy prizmatik chekka dispersiyasi (LOG-210) |
| Haqiqiy optik shisha | `src/lib/glassOptics.ts` + `glass/LiquidGlassEngine.tsx` + `glass/LiquidBackdropCanvas.tsx` + `glass/LiquidGlass3D.tsx` | Chromium da `backdrop-filter: url(#fb-glass-*)` orqali 5 ta Snell sindirish + RGB dispersiya + Fresnel xarita (`pill`, `rail`, `card`, `modal`, `orb`; `x="-6%" y="-6%" width="112%" height="112%"`, `feImage` `0%..100%`, ichki qism 0px buzilish); `html[data-liquid-glass="optical"|"fresnel"]`; binafsha rangsiz WebGL2 ipak fon (`backdrop`) va Hero o'ng panelida 3D ray-traced shisha (`LiquidGlass3D`) |
| Mavzu almashinuvi | `ThemeProvider.toggleTheme(event)` | View Transitions API: bosilgan tugmadan doira; API bo'lmasa — darhol |
| Sanovchi raqam | `motion/CountUp.tsx` | Dashboard raqamlari; server HTML'da yakuniy qiymat |
| Kartalar paydo bo'lishi | `AppStage.revealCards` | Sahifa/tab almashganda ko'rinayotgan tashqi kartalar navbat bilan; qayta mount yo'q |
| Modal, alert, progress | CSS `fb-pop-in`, `fb-scrim-in`, `fb-alert-in`, `fb-fill-in` | Element qo'shilganda avtomatik |

`prefers-reduced-motion: reduce` — barcha animatsiyalar o'chadi (global qoida + `prefersReducedMotion()`).

## 4. Tuzoqlar (o'rganilgan)

- `globals.css` da `@tailwind utilities` boshida, komponent sinflari keyin keladi: bir xil specifiklikda komponent sinfi utilitani bosib ketadi. Shuning uchun komponent sinfida `display` bermang — `hidden sm:inline-flex` kabi utilitlarda qoldiring.
- `backdrop-filter`, `filter`, `transform` bor ota element `position: fixed` bolani qamab qo'yadi — modal/menyular `createPortal(…, document.body)`.
- `.fb-nav-idle` va `.fb-nav-active` `!important` rang beradi; to'q konteyner ichida rangni yuqoriroq specifiklik bilan qayta belgilang (`.fb-section-dock …`). Hover faol bandga tegmasin.
- `bg-[var(--x)]/NN` Tailwind 3 da shaffof chiqadi — `color-mix` ishlating.

> Davomiyliklar (LOG-195, foydalanuvchi so'rovi bilan 3x qisqartirilgan): bosish 55/25 ms, ripple 200 ms, settle 240 ms, kartalar 175 ms (+15 ms qadam), ekran chizig'i 240 ms, sanovchi 240 ms, mavzu doirasi 190 ms, modal 100 ms, scrim 70 ms, alert 90 ms, progress 240 ms.

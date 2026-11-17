# Brauzer E2E skriptlari (staging, haqiqiy akkauntlar)

To'liq tartib: [`docs/operations/STAGING_VA_E2E.md`](../../docs/operations/STAGING_VA_E2E.md).

| Fayl | Vazifa |
| --- | --- |
| `e2e_lib.js` | `BASE` (`E2E_BASE` muhit o'zgaruvchisi), TOTP kodi, qadamlarni yozuvchi `Run` (xato skrinshoti, tarmoq/sahifa xatolari) |
| `e2e_login.js` | 4 rol o'z kirish sahifasida parol + TOTP bilan kiradi; `state_<ROL>.json` saqlaydi |
| `e2e_flow.js` | Rollararo zanjir: e'lon → moderatsiya → nashr/tarif → ariza → chat → kanban → universitet → operator |
| `motion_check.js` | Harakat qatlamini o'lchaydi (glider, ripple, bosish, modal, mavzu doirasi, band holat, reduced-motion) va kadrlar oladi |
| `shell_shots.js` | 8 oyna × (kompyuter yorug'/qorong'i + telefon) skrinshot, sahifa xatosi va gorizontal siljish tekshiruvi |

Qoidalar:

- Hisob ma'lumotlari JSON fayli va natija papkasi **repo tashqarisida** saqlanadi; ularni commit qilmang.
- `e2e_flow.js` dagi chat qadami talaba akkauntining ko'rinadigan nomini (`Audit Talaba …`) qidiradi — boshqa akkaunt ishlatsangiz moslang.
- Skriptlar ma'lumot yaratadi (e'lon, buyurtma, chat xabari) — faqat staging'da ishga tushiring.

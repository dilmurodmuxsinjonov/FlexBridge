# Lokal staging va brauzer E2E

Docker amallari (build, qayta ishga tushirish) faqat foydalanuvchi aniq ruxsat berganda bajariladi (ildizdagi `AGENTS.md`). `infra/.env` mazmuni o'qilmaydi, chop etilmaydi va agentlarga yuborilmaydi — u faqat `--env-file` sifatida beriladi.

## 1. Staging'ni integration kodidan qayta qurish

```bash
cd D:/Codex/FlexBridge-work/integration-ci-green          # integration worktree
git fetch origin && git checkout --detach origin/integration/r1-agent-collaboration
cd infra
docker compose -p flexbridge-r1 -f compose.yaml --env-file D:/FlexBridge/infra/.env up -d --build
```

- `D:/FlexBridge` checkout eski branch'da turishi mumkin — build'ni **worktree'dan** qiling; `.env` faqat `D:/FlexBridge/infra/.env` da.
- `migrate` servisi `alembic upgrade head` ni bajaradi (exit 0 bo'lishi kerak); Postgres/MinIO/ClamAV ma'lumotlari saqlanadi.
- Tekshiruv: `docker ps` (backend/frontend `healthy`), `http://127.0.0.1:3000/` va `http://127.0.0.1:8000/api/v1/opportunities` 200.
- `BFF_SESSION_SECRET` `.env` da bo'lmasa, har qayta ishga tushirishda sessiyalar tugaydi — E2E'dan oldin qayta kiring.

## 2. Sinov akkauntlari

- To'rt rol: talaba (CANDIDATE), korxona egasi (EMPLOYER, OWNER), universitet koordinatori (ACADEMIC, COORDINATOR), operator (OPERATOR, MODERATOR).
- Akkauntlar `scripts/test_unified_auth_all_roles_staging.py` yordamchisi bilan yaratiladi; hisob ma'lumotlari repo **tashqarisidagi** JSON faylda saqlanadi va hech qachon commit qilinmaydi:

```json
{ "CANDIDATE": { "login": { "phone": "+998…", "password": "…", "totp_secret": null } }, "EMPLOYER": { "login": { … } }, "ACADEMIC": { … }, "OPERATOR": { … } }
```

- Staging bazasiga qo'lda soxta `PAID` buyurtma yoki `APPROVED` holat yozilmaydi — faqat UI/API oqimlari.

## 3. Brauzer E2E (`scripts/e2e/`)

Talab: Node.js, Microsoft Edge, `npm install` (`scripts/e2e/package.json` — `playwright-core`).

```bash
cd scripts/e2e && npm install
export E2E_BASE=http://127.0.0.1:3000
OUT=<repo tashqarisidagi papka>
node e2e_login.js   "$OUT" <hisob-ma'lumotlari.json>   # 4 rol UI orqali parol + TOTP; state_<ROL>.json saqlanadi
node e2e_flow.js    "$OUT"   # rollararo zanjir
node motion_check.js "$OUT"  # tugmalar, glider, mavzu, band holat, reduced-motion
node shell_shots.js "$OUT"   # 8 oyna × (kompyuter yorug'/qorong'i + telefon) skrinshot
```

Rollararo zanjir (`e2e_flow.js`): korxona e'lon yaratadi → «Moderatsiyada» → operator «E'lonlar moderatsiyasi» bo'limida tasdiqlaydi → nashr (tarif bo'lmasa kutilgan 409 `ACTIVE_ENTITLEMENT_REQUIRED`) → tarif buyurtmasi → talaba ariza topshiradi → chat (kontakt kod, javob, guruh) → kanban → universitet jadvali va hisobot → operator paneli.

Takroriy ishga tushirishda ikki qadam **kutilganidek** 4xx beradi: takroriy ariza (409 `APPLICATION_ALREADY_EXISTS`) va jadvaldagi vaqt to'qnashuvi (422 `TIMETABLE_SLOT_OVERLAP`); ikkalasida UI aniq xabar ko'rsatadi.

## 4. Oxirgi natija (2026-11-17, integration `a6c3e01`)

- E2E 21/23 (2 tasi yuqoridagi kutilgan tekshiruv), harakat o'lchovi 11/11, 24 skrinshot: sahifa xatosi 0, gorizontal siljish 0.
- Ochiq: to'lov provayderi ulanmagan — buyurtma `PENDING_PAYMENT`, e'lonni UI orqali oxirigacha nashr qilib bo'lmaydi.

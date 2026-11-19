# FlexBridge 1.4 — Serverga yuklash va ishga tushirish qo‘llanmasi

Ushbu qo‘llanma **faqat serverda ishlash uchun zarur bo‘lgan fayllar** paketini yig‘ish, serverga ko‘chirish va `docker compose` orqali ishga tushirish tartibini belgilaydi. Tarixiy AI jurnallari, kunlik `reviews/`, taqdimotlar (`presentations/`) hamda eski `specs/v1_3/` [`archive/`](../../archive/README.md) ga ajratilgan va server paketiga kirmaydi.

---

## 1. Server paketini yig‘ish (lokal kompyuterda)

Repozitoriya ildizida ishga tushiring:

```powershell
python scripts/build_server_package.py
```

Skript faqat runtime fayllarni (`infra/compose.yaml`, `infra/.env.example`, `.dockerignore`, `backend/app`, `backend/alembic`, `backend/scripts`, `specs/v1_4/FlexBridge_model_1_4.json`, `frontend/src` testlarsiz, `frontend/Dockerfile`) yig‘adi va `D:\Codex\FlexBridge-deploy\flexbridge-server-YYYY-MM-DD.tar.gz` hamda uning `.manifest.json` (`sha256`, `file_count`) faylini yaratadi. Maxfiy `.env`, `.git`, `archive/`, `reviews/`, `backend/tests/`, `.sqlite3` va shaxsiy ma’lumotlar **fail-closed** tekshiruv bilan bloklanadi.

---

## 2. Serverga yuklash va ochish

Linux serverda maqsadli papkani tayyorlab, paketni yuklang:

```bash
mkdir -p /opt/flexbridge
scp D:/Codex/FlexBridge-deploy/flexbridge-server-YYYY-MM-DD.tar.gz user@server:/tmp/
ssh user@server "tar -xzf /tmp/flexbridge-server-YYYY-MM-DD.tar.gz -C /opt/flexbridge && rm -f /tmp/flexbridge-server-YYYY-MM-DD.tar.gz"
```

---

## 3. Ishlab chiqarish muhiti (`infra/.env`)

`infra/.env.example` dan nusxa olib haqiqiy qiymatlarni kiriting:

```bash
cd /opt/flexbridge
cp infra/.env.example infra/.env
```

Majburiy o‘zgaruvchilar (`infra/compose.yaml` asosida):

- **PostgreSQL & MinIO**: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `S3_PUBLIC_ENDPOINT_URL`
- **Xavfsizlik kalitlari**:
  - `PAYMENT_WEBHOOK_SECRET`, `AUTH_HMAC_KEY`: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
  - `MFA_ENCRYPTION_KEY`: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
  - `BFF_SESSION_SECRET`: kamida `32` belgili tasodifiy kalit (konteyner qayta ishga tushganda sessiyalar saqlanishi uchun)
- **Domain & WebAuthn & Huquqiy versiyalar**: `WEBAUTHN_RP_ID`, `WEBAUTHN_ORIGIN` (`https://...`), `TERMS_POLICY_VERSION`, `PRIVACY_POLICY_VERSION`
- **Telegram bot (`Q-018`)**: `@FlexBridgeAuthBot` tokeni bilan `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME=FlexBridgeAuthBot`, `TELEGRAM_WEBHOOK_SECRET`, hamda **`TELEGRAM_SIMULATION_MODE=false`**
- **To‘lov shlyuzi (ixtiyoriy, hozircha ulanmagan)**: `/tolovlar` sahifasi provayder ulanmaguncha xavfsiz `PENDING_PAYMENT` holatida ishlaydi; haqiqiy provayder ulanganda `PAYMENT_GATEWAY_URL`, `PAYMENT_GATEWAY_TOKEN`, `PAYMENT_WEBHOOK_SECRET` to‘ldiriladi.

---

## 4. Konteynerlarni qurish, tekshirish va Super Admin ochish

```bash
cd /opt/flexbridge
docker compose -f infra/compose.yaml up -d --build
docker compose -f infra/compose.yaml ps
curl -fsS http://127.0.0.1:8000/api/v1/health/ready
curl -fsS http://127.0.0.1:3000/ >/dev/null
```

Dastlabki Super Admin (`ADMIN`) akkauntini ochish (`backend/scripts/bootstrap_super_admin.py` orqali):

```bash
docker compose -f infra/compose.yaml exec -e SUPER_ADMIN_PASSWORD='<strong-password>' backend \
  python /workspace/backend/scripts/bootstrap_super_admin.py \
  --email admin@example.uz --create --display-name "Platform Admin" \
  --password-env SUPER_ADMIN_PASSWORD --enroll-totp
```

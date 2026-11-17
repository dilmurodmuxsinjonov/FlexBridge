# Telegram bot orqali telefon raqamni tasdiqlash

## Nima o'zgardi (2026-11-16, Issue #226)

Avval sayt "Telegram botni" brauzer ichida o'zi taqlid qilardi: sahifa soxta
`/start` va istalgan telefon raqamli "kontakt" yuborib, javobdan 6 xonali kodni
olardi. Backend webhook'i ham autentifikatsiyasiz edi va kodni javobda qaytarardi.
Natijada istalgan raqamni "tasdiqlash" mumkin edi.

Endi uchta rejim bor (`GET /api/v1/auth/options` -> `telegram_mode`):

| Rejim | Qachon | Xatti-harakat |
|---|---|---|
| `LIVE` | `TELEGRAM_BOT_TOKEN` berilgan | Haqiqiy bot. Kod faqat foydalanuvchining Telegram chatiga yuboriladi. Webhook faqat Telegram'ning `secret_token` sarlavhasi bilan qabul qilinadi. |
| `SIMULATION` | Token yo'q va `TELEGRAM_SIMULATION_MODE=true` | Faqat lokal staging testlari uchun: eski skriptlar ishlashi uchun webhook kodni qaytaradi. Saytda "Sinov rejimi" deb yoziladi. Ochiq serverda **yoqmang**. |
| `DISABLED` | Token yo'q, simulyatsiya yoqilmagan | Telegram tanlovi o'chiriladi, faqat SMS. |

Token berilsa, simulyatsiya bayrog'i e'tiborga olinmaydi (`LIVE` ustun).

## Botni ishga tushirish (siz bajarasiz)

1. Telegram'da **@BotFather** -> `/newbot` -> nom va `...bot` bilan tugaydigan
   username bering. BotFather tokenni beradi (`123456789:AA...`).
2. `D:\FlexBridge\infra\.env` fayliga qo'shing (bu fayl Git'ga tushmaydi):

   ```env
   TELEGRAM_BOT_TOKEN=123456789:AA...
   TELEGRAM_BOT_USERNAME=SizningBotingiz_bot
   ```

   `TELEGRAM_BOT_USERNAME` ixtiyoriy: berilmasa backend uni `getMe` orqali o'zi aniqlaydi.
3. Stack'ni qayta ishga tushiring: `docker compose -f infra/compose.yaml up -d --build`.
   `telegram-bot` servisi Telegram'dan yangilanishlarni **polling** (getUpdates)
   orqali oladi, shuning uchun ochiq HTTPS manzil kerak emas.
4. Tekshirish: `docker compose -f infra/compose.yaml logs telegram-bot` ichida
   `Connected as @SizningBotingiz_bot` chiqishi kerak. Saytda ro'yxatdan o'tishda
   "Telegram" tanlang -> "Telegramda ochish" -> Start -> "📱 Telefon raqamni yuborish"
   -> bot yuborgan kodni saytga kiriting.

## Ochiq domen (production) uchun webhook

Polling bitta server uchun yetarli. Webhook ishlatmoqchi bo'lsangiz:

```env
TELEGRAM_WEBHOOK_SECRET=<16+ belgili tasodifiy qator: A-Z a-z 0-9 _ ->
```

```powershell
docker compose -f infra/compose.yaml run --rm telegram-bot python -m app.workers.telegram_bot_poller --set-webhook https://<domen>/api/bff/auth/telegram/webhook
```

Webhook ro'yxatdan o'tgach `telegram-bot` servisini to'xtating (Bot API getUpdates
va webhook'ni bir vaqtda qo'llamaydi). Pollingga qaytish:
`... telegram_bot_poller --delete-webhook`.

## Xavfsizlik qoidalari

- Kontakt faqat Telegram'ning tugmasi orqali qabul qilinadi va `contact.user_id`
  yuboruvchiga teng bo'lishi shart (boshqa odamning kontaktini forward qilib bo'lmaydi).
- Telegram'dagi raqam saytda kiritilgan raqamga aynan mos bo'lishi kerak.
- `LIVE` rejimda webhook javobida kod yoki bot matni qaytarilmaydi; xatolar 200 bilan
  qaytadi (Telegram qayta yubormasligi uchun), foydalanuvchiga bot o'zi tushuntiradi.
- Rate-limit Telegram foydalanuvchisi bo'yicha (`tg:<id>`).
- Token hech qachon log'ga yozilmaydi.
- Testlar: `backend/tests/security/test_telegram_bot.py`,
  `frontend/src/components/TelegramVerification.test.tsx`.

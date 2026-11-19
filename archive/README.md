# FlexBridge Arxivi (`archive/`)

Ushbu katalog **faqat tarixiy yozuvlar, avvalgi texnik tekshiruvlar va endilikda serverda ishlash uchun shart bo‘lmagan hujjatlarni** saqlash uchun ajratilgan.

> **Muhim:** Serverga (`docker compose` / production) ko‘tariladigan ilova bu katalogdagi hech bir faylga tayanmaydi. Minimal server paketini yig‘ish uchun [`scripts/build_server_package.py`](../scripts/build_server_package.py) dan foydalaning (`archive/` to‘liq chiqarib tashlanadi).

## Tarkibi

| Papka | Vazifasi | Avvalgi joyi |
| --- | --- | --- |
| [`ai-history/journals/`](ai-history/journals) | AI ish tarixi (`LOG-001..LOG-169`), eski holat qatorlari va texnik qarorlar arxivi | `docs/journals/archive/` |
| [`ai-history/protocols/`](ai-history/protocols) | Agent topshiruv (`handoff`) tarixiy bo‘limlari | `docs/protocols/archive/` |
| [`reviews/`](reviews) | `2026-11-07..2026-11-15` kunlik audit, review, skrinshot hisobotlari va `legacy_tests` SHA-256 nazorat to‘plami | `reviews/` |
| [`presentations/`](presentations) | Texnik topshiriq PDF, investor va ustoz uchun taqdimot fayllari | `docs/presentations/` |
| [`specs/v1_3/`](specs/v1_3) | `1.4` bazaviy modelidan (`specs/v1_4/`) oldingi `1.3` spetsifikatsiyalar to‘plami | `specs/v1_3/` |

Lokal Git’ga kiritilmagan agent vaqtinchalik papkalari (`.agents`, `.claude`, `.gemini`) hamda eski SQLite / log qoldiqlari lokal arxiv papkasiga (`D:\Codex\FlexBridge-archive\2026-11-19\`) ko‘chirildi.

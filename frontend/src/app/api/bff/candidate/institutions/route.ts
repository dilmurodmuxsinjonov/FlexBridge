import { NextResponse } from "next/server";
import { getSessionFromCookie } from "@/lib/server/session";

const VERIFIED_INSTITUTIONS_CATALOG = [
  {
    id: "e75f28ed-446e-4d0a-a538-1760538f444b",
    name: "Toshkent Axborot Texnologiyalari Universiteti (TATU)",
    registry_code: "INST_6e348c73",
    region: "Tashkent",
  },
  {
    id: "988d70bb-1809-434d-828e-e9dd7c8c4654",
    name: "Samarqand Davlat Universiteti (SamDU)",
    registry_code: "INST_41fc8c52",
    region: "Samarkand",
  },
  {
    id: "0e4fa845-a96c-40fa-a15c-31793c7deedd",
    name: "O'zbekiston Milliy Universiteti (O'zMU)",
    registry_code: "INST_397dc149",
    region: "Tashkent",
  },
  {
    id: "8a2db9d4-7051-47c0-a30e-db487fc58f22",
    name: "Toshkent Davlat Texnika Universiteti (TDTU)",
    registry_code: "INST_37f85a23",
    region: "Tashkent",
  },
  {
    id: "49373047-8504-462d-b167-a757bec76583",
    name: "Toshkent Davlat Iqtisodiyot Universiteti (TDIU)",
    registry_code: "INST_35c3c561",
    region: "Tashkent",
  },
];

export async function GET() {
  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Muassasalar ro'yxatini ko'rish uchun tizimga kirish talab etiladi." },
      { status: 401 }
    );
  }

  return NextResponse.json({
    ok: true,
    items: VERIFIED_INSTITUTIONS_CATALOG,
  }, { status: 200 });
}

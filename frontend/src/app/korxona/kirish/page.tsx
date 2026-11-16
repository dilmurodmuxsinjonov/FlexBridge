"use client";

import { Briefcase, Building2, ClipboardCheck, CreditCard, Users } from "lucide-react";
import { LoginScreen, type LoginPanelConfig } from "@/components/auth/LoginPanel";

const CONFIG: LoginPanelConfig = {
  portal: "EMPLOYER",
  tone: "emerald",
  icon: Building2,
  badge: "Korxona kirishi",
  audience: "korxona",
  title: "Korxona kabinetiga kirish",
  subtitle: "Tashkilot rahbari, HR yoki mentor hisobingiz bilan kiring.",
  identifierPlaceholder: "+998 90 123 45 67 yoki hr@korxona.uz",
  submitLabel: "Kirish",
  home: "/employer",
  redirectPrefixes: ["/employer"],
  register: { href: "/korxona/royxatdan-otish", label: "Korxonani ro‘yxatdan o‘tkazish" },
  asideTitle: "Ish beruvchilar uchun",
  asideText: "Tasdiqlangan talabalarni toping, e’lon joylang va amaliyotni bir joyda boshqaring.",
  features: [
    { icon: Briefcase, title: "Vakansiyalar", desc: "Ish va amaliyot e’lonlarini joylash va boshqarish." },
    { icon: Users, title: "Nomzodlar", desc: "Arizalarni bosqichma-bosqich ko‘rib chiqish va mos talabalarni qidirish." },
    { icon: ClipboardCheck, title: "Mentorlik", desc: "Talaba kundaliklarini tasdiqlash va elektron imzo." },
    { icon: CreditCard, title: "Jamoa va to‘lovlar", desc: "Xodimlarni taklif qilish, tarif va kvotalar." },
  ],
};

export default function KorxonaKirishPage() {
  return <LoginScreen config={CONFIG} />;
}

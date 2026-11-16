"use client";

import { BadgeCheck, KeyRound, LifeBuoy, ScrollText, ShieldCheck } from "lucide-react";
import { LoginScreen, type LoginPanelConfig } from "@/components/auth/LoginPanel";

const CONFIG: LoginPanelConfig = {
  portal: "OPERATOR",
  tone: "amber",
  icon: ShieldCheck,
  badge: "Operator kirishi",
  audience: "platforma operatori",
  title: "Operator paneliga kirish",
  subtitle: "Faqat FlexBridge platforma xodimlari uchun. Kirish ikki bosqichli tasdiqlash bilan himoyalangan.",
  identifierPlaceholder: "operator@flexbridge.uz",
  submitLabel: "Kirish",
  home: "/operator",
  redirectPrefixes: ["/operator"],
  register: null,
  registerNote: "Operator hisoblari faqat administrator tomonidan beriladi.",
  asideTitle: "Platforma xodimlari uchun",
  asideText: "Platformaning ishonchliligi va xavfsizligini ta’minlaydigan ish joyi.",
  features: [
    { icon: BadgeCheck, title: "Tashkilotlarni tekshirish", desc: "Korxona va universitet arizalarini ko‘rib chiqish." },
    { icon: ScrollText, title: "Audit jurnali", desc: "Barcha muhim amallar o‘zgarmas jurnalda saqlanadi." },
    { icon: KeyRound, title: "Maxsus ruxsatlar", desc: "Favqulodda kirish faqat ikki xodim tasdig‘i bilan." },
    { icon: LifeBuoy, title: "Yordam murojaatlari", desc: "Foydalanuvchilar murojaatlariga javob berish." },
  ],
};

export default function OperatorKirishPage() {
  return <LoginScreen config={CONFIG} />;
}

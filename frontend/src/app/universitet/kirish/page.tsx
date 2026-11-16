"use client";

import { Award, BookOpen, CalendarDays, GraduationCap, Landmark } from "lucide-react";
import { LoginScreen, type LoginPanelConfig } from "@/components/auth/LoginPanel";

const CONFIG: LoginPanelConfig = {
  portal: "ACADEMIC",
  tone: "indigo",
  icon: Landmark,
  badge: "Universitet kirishi",
  audience: "universitet xodimi",
  title: "Universitet kabinetiga kirish",
  subtitle: "Dekanat, kafedra yoki amaliyot koordinatori hisobingiz bilan kiring.",
  identifierPlaceholder: "+998 90 123 45 67 yoki xodim@otm.uz",
  submitLabel: "Kirish",
  home: "/university",
  redirectPrefixes: ["/university"],
  register: { href: "/universitet/royxatdan-otish", label: "Universitetni ulash" },
  asideTitle: "Universitet xodimlari uchun",
  asideText: "Talabalaringizning ishi va amaliyotini kuzatib boring, o‘qish bilan muvozanatni saqlang.",
  features: [
    { icon: GraduationCap, title: "Talabalikni tasdiqlash", desc: "Talabalarning o‘qish holati bo‘yicha so‘rovlarini ko‘rib chiqish." },
    { icon: BookOpen, title: "Amaliyot nazorati", desc: "Kundaliklar, biriktirilgan rahbarlar va yakuniy xulosalar." },
    { icon: CalendarDays, title: "Dars jadvali", desc: "Jadvalni yuklang — talabalarga mos ish vaqtlari hisoblanadi." },
    { icon: Award, title: "Baholash", desc: "Amaliyot natijalarini baholash va hisobotlar." },
  ],
};

export default function UniversitetKirishPage() {
  return <LoginScreen config={CONFIG} />;
}

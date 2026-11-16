"use client";

import { Building2, GraduationCap, Landmark, ShieldCheck } from "lucide-react";
import { LoginScreen, type LoginPanelConfig } from "@/components/auth/LoginPanel";

const CONFIG: LoginPanelConfig = {
  tone: "orange",
  icon: ShieldCheck,
  badge: "FlexBridge hisobi",
  title: "Hisobingizga kiring",
  subtitle: "Talaba, korxona, universitet va operatorlar uchun yagona kirish. Kirgach, o‘z kabinetingizga avtomatik o‘tasiz.",
  identifierPlaceholder: "+998 90 123 45 67 yoki pochta@misol.uz",
  submitLabel: "Kirish",
  register: { href: "/royxatdan-otish", label: "Ro‘yxatdan o‘tish" },
  asideTitle: "Bitta hisob — o‘z kabinetingiz",
  asideText: "FlexBridge rolingizni o‘zi aniqlaydi va sizni kerakli bo‘limga olib boradi.",
  features: [
    { icon: GraduationCap, title: "Talaba", desc: "Rezyume, dars jadvaliga mos ishlar, arizalar va amaliyot kundaligi." },
    { icon: Building2, title: "Korxona", desc: "Vakansiyalar, kelgan arizalar va mos talabalarni qidirish." },
    { icon: Landmark, title: "Universitet", desc: "Talabalikni tasdiqlash, amaliyotni kuzatish va baholash." },
    { icon: ShieldCheck, title: "Operator", desc: "Tashkilotlarni tekshirish va platforma xavfsizligi." },
  ],
};

export default function KirishPage() {
  return <LoginScreen config={CONFIG} />;
}

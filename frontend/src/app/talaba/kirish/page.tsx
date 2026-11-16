"use client";

import { Award, BookOpen, FileText, GraduationCap, Search } from "lucide-react";
import { LoginScreen, type LoginPanelConfig } from "@/components/auth/LoginPanel";

const CONFIG: LoginPanelConfig = {
  portal: "CANDIDATE",
  tone: "sky",
  icon: GraduationCap,
  badge: "Talaba kirishi",
  audience: "talaba",
  title: "Talaba kabinetiga kirish",
  subtitle: "Rezyume, arizalar va amaliyot kundaligingiz shu yerda.",
  identifierPlaceholder: "+998 90 123 45 67 yoki talaba@otm.uz",
  submitLabel: "Kirish",
  home: "/nomzod",
  redirectPrefixes: ["/nomzod", "/ishlar"],
  register: { href: "/talaba/royxatdan-otish", label: "Talaba sifatida ro‘yxatdan o‘tish" },
  asideTitle: "Talabalar uchun",
  asideText: "O‘qishingizga xalaqit bermaydigan ish va amaliyot topish uchun kerakli hamma narsa bir joyda.",
  features: [
    { icon: FileText, title: "Rezyume va ko‘nikmalar", desc: "Bir marta to‘ldiring — ish beruvchilar sizni qidiruvda topadi." },
    { icon: Search, title: "Jadvalga mos ishlar", desc: "Dars jadvalingiz bilan to‘qnashmaydigan smenali ish va amaliyotlar." },
    { icon: BookOpen, title: "Shartnoma va kundalik", desc: "Amaliyot shartnomasi, kundalik va elektron imzo bir joyda." },
    { icon: Award, title: "Baholar", desc: "Amaliyot natijalari va kerak bo‘lsa apellyatsiya." },
  ],
};

export default function TalabaKirishPage() {
  return <LoginScreen config={CONFIG} back={{ href: "/", label: "E’lonlar katalogi" }} />;
}

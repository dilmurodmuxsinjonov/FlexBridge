import type { Metadata } from "next";
import PasswordRecovery from "@/components/auth/PasswordRecovery";

export const metadata: Metadata = {
  title: "Parolni tiklash — FlexBridge",
  description: "FlexBridge hisobiga qayta kirish: telefon yoki pochta orqali kod va qo‘shimcha tasdiq bilan yangi parol o‘rnatish.",
};

export default function ParolniTiklashPage() {
  return <PasswordRecovery />;
}

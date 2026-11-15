"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldCheck,
  CheckCircle2,
  FileText,
  Lock,
  Compass,
  Briefcase,
  Building2,
  User,
  Search,
  GraduationCap,
} from "lucide-react";
import { fetchAuthMe, type AuthUser } from "@/lib/api";
import {
  isAcademicOnlyRoles,
  isEmployerOnlyRoles,
  isOperatorOnlyRoles,
  isStudentOnlyRoles,
} from "@/lib/roles";

function isStudentOnlyUser(user: AuthUser | null): boolean {
  return Boolean(user && isStudentOnlyRoles(user.roles));
}

export default function Footer() {
  const pathname = usePathname();
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    let active = true;
    const syncAuth = () => {
      fetchAuthMe()
        .then((user) => {
          if (active) setCurrentUser(user);
        })
        .catch(() => {
          if (active) setCurrentUser(null);
        });
    };
    syncAuth();
    window.addEventListener("flexbridge:auth-changed", syncAuth);
    return () => {
      active = false;
      window.removeEventListener("flexbridge:auth-changed", syncAuth);
    };
  }, [pathname]);

  const isStudentScope =
    Boolean(pathname?.startsWith("/nomzod")) ||
    Boolean(pathname?.startsWith("/talaba")) ||
    isStudentOnlyUser(currentUser);
  const isEmployerScope =
    !isStudentScope &&
    (Boolean(pathname?.startsWith("/employer")) ||
      Boolean(pathname?.startsWith("/korxona")) ||
      Boolean(currentUser && isEmployerOnlyRoles(currentUser.roles)));
  const isUniversityScope =
    !isStudentScope &&
    !isEmployerScope &&
    (Boolean(pathname?.startsWith("/university")) ||
      Boolean(pathname?.startsWith("/universitet")) ||
      Boolean(currentUser && isAcademicOnlyRoles(currentUser.roles)));
  const isOperatorScope =
    !isStudentScope &&
    !isEmployerScope &&
    !isUniversityScope &&
    (Boolean(pathname?.startsWith("/operator")) ||
      Boolean(currentUser && isOperatorOnlyRoles(currentUser.roles)));
  return (
    <footer className="mt-auto w-full px-3 sm:px-6 pb-24 pt-6 text-[var(--fb-ink-muted)] text-xs">
      <div className="max-w-[1440px] mx-auto skeuo-card rounded-[28px] overflow-hidden">
      {/* Main Directory Links */}
      <div className="px-5 sm:px-8 lg:px-10 py-10 md:py-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-8">
          {/* Column 1: Brand & Mission */}
          <div className="space-y-3">
            <Link href="/" className="inline-flex items-center gap-2 select-none group">
              <div className="w-7 h-7 rounded bg-primary flex items-center justify-center text-white shadow-sm font-bold text-sm tracking-wider">
                FB
              </div>
              <span className="font-heading font-bold text-base tracking-tight text-white group-hover:text-primary transition-colors">
                FlexBridge
              </span>
              <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-white/[0.06] text-primary border border-primary/20 tracking-wider">
                v1.4
              </span>
            </Link>

            <p className="text-[11px] text-zinc-400 leading-relaxed max-w-xs">
              O&apos;zbekiston talabalari uchun moslashuvchan ish va amaliyot imkoniyatlarini taqdim etuvchi
              yagona rasmiy ekotizim.
            </p>

            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>100% Tirik Staging Integratsiya</span>
            </div>
          </div>

          {/* Column 2: Core Portals */}
          <div className="space-y-3">
            <h4 className="text-[11px] font-bold uppercase tracking-wider text-zinc-200">
              {isStudentScope
                ? "Talaba Bo‘limlari"
                : isEmployerScope
                  ? "Korxona Bo‘limlari"
                  : isUniversityScope
                    ? "OTM Bo‘limlari"
                    : isOperatorScope
                      ? "SOC Terminal Bo‘limlari"
                      : "Platforma Portallari"}
            </h4>
            <ul className="space-y-2 text-[11px]">
              {isOperatorScope ? (
                <>
                  <li>
                    <Link href="/operator" className="hover:text-white transition flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                      <span>Operator SOC Terminali</span>
                    </Link>
                  </li>
                  <li>
                    <Link href="/operator/kirish" className="hover:text-white transition flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5 text-amber-400" />
                      <span>SOC Alohida Kirishi</span>
                    </Link>
                  </li>
                  <li>
                    <Link href="/" className="hover:text-white transition flex items-center gap-1.5">
                      <Search className="w-3.5 h-3.5 text-zinc-500" />
                      <span>Bosh Sahifa & Katalog</span>
                    </Link>
                  </li>
                </>
              ) : isUniversityScope ? (
                <>
                  <li>
                    <Link href="/university" className="hover:text-white transition flex items-center gap-1.5">
                      <GraduationCap className="w-3.5 h-3.5 text-indigo-400" />
                      <span>OTM Akademik Portal</span>
                    </Link>
                  </li>
                  <li>
                    <Link href="/universitet/kirish" className="hover:text-white transition flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5 text-indigo-400" />
                      <span>OTM Kirishi (Alohida)</span>
                    </Link>
                  </li>
                  <li>
                    <Link href="/universitet/royxatdan-otish" className="hover:text-white transition flex items-center gap-1.5">
                      <Building2 className="w-3.5 h-3.5 text-indigo-400" />
                      <span>OTM Vakili Ulanishi</span>
                    </Link>
                  </li>
                  <li>
                    <Link href="/" className="hover:text-white transition flex items-center gap-1.5">
                      <Search className="w-3.5 h-3.5 text-zinc-500" />
                      <span>Bosh Sahifa & Katalog</span>
                    </Link>
                  </li>
                </>
              ) : isEmployerScope ? (
                <>
                  <li>
                    <Link href="/employer" className="hover:text-white transition flex items-center gap-1.5">
                      <Briefcase className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Korxona & HR Kabineti</span>
                    </Link>
                  </li>
                  <li>
                    <Link href="/korxona/kirish" className="hover:text-white transition flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Korxona Kirishi (Alohida)</span>
                    </Link>
                  </li>
                  <li>
                    <Link href="/korxona/royxatdan-otish" className="hover:text-white transition flex items-center gap-1.5">
                      <Building2 className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Korxona Vakili Ro‘yxatdan O‘tish</span>
                    </Link>
                  </li>
                  <li>
                    <Link href="/" className="hover:text-white transition flex items-center gap-1.5">
                      <Search className="w-3.5 h-3.5 text-zinc-500" />
                      <span>Bosh Sahifa & Katalog</span>
                    </Link>
                  </li>
                </>
              ) : (
                <>
                  <li>
                    <Link href="/" className="hover:text-white transition flex items-center gap-1.5">
                      <Search className="w-3.5 h-3.5 text-zinc-500" />
                      <span>Bo‘sh Ish O‘rinlari Katalogi</span>
                    </Link>
                  </li>
                  <li>
                    <Link href="/nomzod" className="hover:text-white transition flex items-center gap-1.5">
                      <User className="w-3.5 h-3.5 text-zinc-500" />
                      <span>Nomzod & Talaba Kabineti</span>
                    </Link>
                  </li>
                  {isStudentScope ? (
                    <li>
                      <Link
                        href="/talaba/kirish"
                        className="hover:text-white transition flex items-center gap-1.5"
                      >
                        <Lock className="w-3.5 h-3.5 text-sky-400" />
                        <span>Talaba Kirishi (Alohida)</span>
                      </Link>
                    </li>
                  ) : (
                    <>
                      <li>
                        <Link href="/employer" className="hover:text-white transition flex items-center gap-1.5">
                          <Briefcase className="w-3.5 h-3.5 text-zinc-500" />
                          <span>Ish Beruvchi HR Kabineti</span>
                        </Link>
                      </li>
                      <li>
                        <Link href="/university" className="hover:text-white transition flex items-center gap-1.5">
                          <Building2 className="w-3.5 h-3.5 text-zinc-500" />
                          <span>Universitet Koordinatori</span>
                        </Link>
                      </li>
                      <li>
                        <Link href="/operator" className="hover:text-white transition flex items-center gap-1.5">
                          <Lock className="w-3.5 h-3.5 text-zinc-500" />
                          <span>Platforma Operatori SOC</span>
                        </Link>
                      </li>
                    </>
                  )}
                </>
              )}
            </ul>
          </div>

          {/* Column 3: Services */}
          <div className="space-y-3">
            <h4 className="text-[11px] font-bold uppercase tracking-wider text-zinc-200">
              {isOperatorScope
                ? "SOC Xizmatlari"
                : isUniversityScope
                  ? "OTM Xizmatlari"
                  : isEmployerScope
                    ? "Korxona Xizmatlari"
                    : "Nomzod Xizmatlari"}
            </h4>
            {isOperatorScope ? (
              <ul className="space-y-2 text-[11px]">
                <li>
                  <Link href="/operator" className="hover:text-white transition">
                    Hash-Chain Audit & Tizim Hodisalari
                  </Link>
                </li>
                <li>
                  <Link href="/operator" className="hover:text-white transition">
                    KYB, OTM & Talaba Moderatsiya Navbati
                  </Link>
                </li>
                <li>
                  <Link href="/operator" className="hover:text-white transition">
                    Moliya, Ledger & Qaytarish Nazorati
                  </Link>
                </li>
                <li>
                  <Link href="/operator" className="hover:text-white transition">
                    Yordam Tiketlari & Insidentlar
                  </Link>
                </li>
              </ul>
            ) : isUniversityScope ? (
              <ul className="space-y-2 text-[11px]">
                <li>
                  <Link href="/university" className="hover:text-white transition">
                    Amaliyot Kundaliklari Tekshiruvi
                  </Link>
                </li>
                <li>
                  <Link href="/university" className="hover:text-white transition">
                    Yakuniy Akademik Xulosalar & E-Imzo
                  </Link>
                </li>
                <li>
                  <Link href="/university" className="hover:text-white transition">
                    Kafedra Taqsimoti & Dars Jadvali
                  </Link>
                </li>
                <li>
                  <Link href="/university" className="hover:text-white transition">
                    O‘qituvchi Vakolat & Tasdiqlash
                  </Link>
                </li>
              </ul>
            ) : isEmployerScope ? (
              <ul className="space-y-2 text-[11px]">
                <li>
                  <Link href="/employer" className="hover:text-white transition">
                    Vakansiyalar & Nomzod Kanban
                  </Link>
                </li>
                <li>
                  <Link href="/employer" className="hover:text-white transition">
                    Amaliyot Shartnomalari & Mentor E-Imzo
                  </Link>
                </li>
                <li>
                  <Link href="/employer" className="hover:text-white transition">
                    Korxona Profili, Jamoa & Takliflar
                  </Link>
                </li>
                <li>
                  <Link href="/employer" className="hover:text-white transition">
                    Obuna, Kvota & To‘lovlar
                  </Link>
                </li>
              </ul>
            ) : (
              <ul className="space-y-2 text-[11px]">
                <li>
                  <Link href="/nomzod/arizalar" className="hover:text-white transition">
                    Arizalarim & Suhbatlar
                  </Link>
                </li>
                <li>
                  <Link href="/nomzod/shartnomalar" className="hover:text-white transition">
                    Amaliyot Shartnomalari (API-030/050)
                  </Link>
                </li>
                <li>
                  <Link href="/nomzod/kundalik" className="hover:text-white transition">
                    Kunlik Amaliyot Kundaligi
                  </Link>
                </li>
                <li>
                  <Link href="/nomzod/saqlanganlar" className="hover:text-white transition">
                    Saqlangan E‘lonlar (Bookmarks)
                  </Link>
                </li>
                <li>
                  <Link href="/nomzod/baholar" className="hover:text-white transition">
                    Reytinglar & Sharhlar
                  </Link>
                </li>
                <li>
                  <Link href="/nomzod/xavfsizlik" className="hover:text-white transition">
                    Xavfsizlik, 2FA & Sessiyalar
                  </Link>
                </li>
              </ul>
            )}
          </div>

          {/* Column 4: Legal & CMS */}
          <div className="space-y-3">
            <h4 className="text-[11px] font-bold uppercase tracking-wider text-zinc-200">
              Qonuniy & Yordam (CMS)
            </h4>
            <ul className="space-y-2 text-[11px]">
              <li>
                <Link href="/shartlar" className="hover:text-white transition flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-primary" />
                  <span>Foydalanish Shartlari (Terms)</span>
                </Link>
              </li>
              <li>
                <Link href="/maxfiylik" className="hover:text-white transition flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Maxfiylik Siyosati (Privacy)</span>
                </Link>
              </li>
              <li>
                <Link href="/haqida" className="hover:text-white transition flex items-center gap-1.5">
                  <Compass className="w-3.5 h-3.5 text-sky-400" />
                  <span>Platforma Haqida & Qo‘llanmalar</span>
                </Link>
              </li>
              <li>
                <Link href="/nomzod/yordam" className="hover:text-white transition">
                  Texnik Qo‘llab-Quvvatlash & Chiptalar
                </Link>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Bottom Legal Bar */}
      <div className="border-t border-[var(--fb-border)] skeuo-well rounded-none border-x-0 border-b-0 py-5 px-5 sm:px-8 lg:px-10">
        <div className="max-w-[1440px] mx-auto flex flex-col md:flex-row md:items-center justify-between gap-3 text-[11px] text-[var(--fb-ink-muted)] font-mono">
          <div className="flex flex-wrap items-center gap-4">
            <p>© 2026 FlexBridge Inc. Barcha huquqlar himoyalangan.</p>
            <span className="hidden sm:inline text-zinc-700">|</span>
            <span className="flex items-center gap-1 text-zinc-400">
              <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
              O‘zR Mehnat Kodeksi 118-modda (kunlik 8-soatlik chegara)
            </span>
          </div>

          <div className="flex items-center gap-4">
            <span>HEMIS v3.2 Integratsiyasi</span>
            <span className="text-zinc-700">•</span>
            <span>SHA-256 Kriptografik Audit</span>
          </div>
        </div>
      </div>
      </div>
    </footer>
  );
}


"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import {
  User,
  Sparkles,
  Calendar,
  Clock,
  MapPin,
  Briefcase,
  Save,
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  LogIn,
  LogOut,
  ShieldCheck,
  FileText,
  Search,
  Check,
} from "lucide-react";
import {
  fetchAuthMe,
  fetchCandidateProfile,
  updateCandidateProfile,
  fetchCatalogSkills,
  updateCandidateSkills,
  fetchCandidateAvailability,
  saveCandidateAvailability,
  logoutUser,
  AuthUser,
  CandidateProfileData,
  CandidateProfileSkill,
  CatalogSkillItem,
  AvailabilityRuleItem,
} from "@/lib/api";
import AuthModal from "@/components/AuthModal";

const UZBEKISTAN_REGIONS = [
  "Toshkent shahri",
  "Toshkent viloyati",
  "Samarqand",
  "Farg‘ona",
  "Andijon",
  "Namangan",
  "Buxoro",
  "Xorazm",
  "Qashqadaryo",
  "Surxondaryo",
  "Jizzax",
  "Sirdaryo",
  "Navoiy",
  "Qoraqalpog‘iston Respublikasi",
];

const WEEKDAY_NAMES = [
  { id: 1, name: "Dushanba" },
  { id: 2, name: "Seshanba" },
  { id: 3, name: "Chorshanba" },
  { id: 4, name: "Payshanba" },
  { id: 5, name: "Juma" },
  { id: 6, name: "Shanba" },
  { id: 7, name: "Yakshanba" },
];

function minutesToTimeString(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function timeStringToMinutes(timeStr: string): number {
  const [h, m] = timeStr.split(":").map(Number);
  return (h || 0) * 60 + (m || 0);
}

export default function CandidateProfileHub() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // Active Tab: PROFILE, SKILLS, AVAILABILITY
  const [activeTab, setActiveTab] = useState<"PROFILE" | "SKILLS" | "AVAILABILITY">("PROFILE");

  // Tab 1: Profile state
  const [profile, setProfile] = useState<CandidateProfileData | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [profileHeadline, setProfileHeadline] = useState("");
  const [profileRegion, setProfileRegion] = useState("Toshkent shahri");
  const [profileBio, setProfileBio] = useState("");
  const [profileExpMonths, setProfileExpMonths] = useState<number>(0);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileSuccessMsg, setProfileSuccessMsg] = useState<string | null>(null);
  const [profileErrorMsg, setProfileErrorMsg] = useState<string | null>(null);

  // Tab 2: Skills state
  const [catalogSkills, setCatalogSkills] = useState<CatalogSkillItem[]>([]);
  const [skillSearchQuery, setSkillSearchQuery] = useState("");
  const [selectedCatalogSkillId, setSelectedCatalogSkillId] = useState("");
  const [selectedSkillLevel, setSelectedSkillLevel] = useState("INTERMEDIATE");
  const [mySkills, setMySkills] = useState<CandidateProfileSkill[]>([]);
  const [isSavingSkills, setIsSavingSkills] = useState(false);
  const [skillsSuccessMsg, setSkillsSuccessMsg] = useState<string | null>(null);
  const [skillsErrorMsg, setSkillsErrorMsg] = useState<string | null>(null);

  // Tab 3: Availability state
  const [rules, setRules] = useState<AvailabilityRuleItem[]>([]);
  const [isLoadingAvailability, setIsLoadingAvailability] = useState(false);
  const [isSavingAvailability, setIsSavingAvailability] = useState(false);
  const [availSuccessMsg, setAvailSuccessMsg] = useState<string | null>(null);
  const [availErrorMsg, setAvailErrorMsg] = useState<string | null>(null);

  // Load Profile & Skills
  const loadProfileData = useCallback(async () => {
    setIsLoadingProfile(true);
    setProfileErrorMsg(null);
    try {
      const data = await fetchCandidateProfile();
      setProfile(data);
      setProfileHeadline(data.headline || "");
      setProfileRegion(data.region || "Toshkent shahri");
      setProfileBio(data.bio || "");
      setProfileExpMonths(data.experience_months || 0);
      setMySkills(data.skills || []);
    } catch (err: unknown) {
      setProfileErrorMsg(err instanceof Error ? err.message : "Profil ma'lumotlarini yuklashda xatolik");
    } finally {
      setIsLoadingProfile(false);
    }
  }, []);

  // Load Catalog Skills
  const loadCatalog = useCallback(async (q = "") => {
    try {
      const items = await fetchCatalogSkills(q);
      setCatalogSkills(items);
      if (items.length > 0 && !selectedCatalogSkillId) {
        setSelectedCatalogSkillId(items[0].id);
      }
    } catch {
      // Non-blocking
    }
  }, [selectedCatalogSkillId]);

  // Load Availability Rules
  const loadAvailabilityData = useCallback(async () => {
    setIsLoadingAvailability(true);
    setAvailErrorMsg(null);
    try {
      const data = await fetchCandidateAvailability();
      setRules(data.rules || []);
    } catch (err: unknown) {
      setAvailErrorMsg(err instanceof Error ? err.message : "Jadval ma'lumotlarini yuklashda xatolik");
    } finally {
      setIsLoadingAvailability(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    fetchAuthMe().then((user) => {
      if (isMounted) {
        setCurrentUser(user);
        setIsAuthLoading(false);
        if (user) {
          loadProfileData();
          loadCatalog();
          loadAvailabilityData();
        }
      }
    });
    return () => {
      isMounted = false;
    };
  }, [loadProfileData, loadCatalog, loadAvailabilityData]);

  // Handle Logout
  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    setProfile(null);
    setMySkills([]);
    setRules([]);
  };

  // Handle Profile Save (API-026)
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    setProfileSuccessMsg(null);
    setProfileErrorMsg(null);

    if (!profileHeadline.trim()) {
      setProfileErrorMsg("Kasbiy sarlavha (headline) kiritilishi shart.");
      setIsSavingProfile(false);
      return;
    }

    try {
      await updateCandidateProfile({
        headline: profileHeadline.trim(),
        region: profileRegion,
        bio: profileBio.trim() || null,
        experience_months: Number(profileExpMonths) || 0,
      });
      setProfileSuccessMsg("Profil ma'lumotlari muvaffaqiyatli saqlandi.");
      await loadProfileData();
    } catch (err: unknown) {
      setProfileErrorMsg(err instanceof Error ? err.message : "Profilni saqlashda xatolik yuz berdi");
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Handle Add Skill to list
  const handleAddSkill = () => {
    if (!selectedCatalogSkillId) return;
    const catalogItem = catalogSkills.find((c) => c.id === selectedCatalogSkillId);
    if (!catalogItem) return;

    if (mySkills.some((s) => s.skill_id === catalogItem.id)) {
      setSkillsErrorMsg("Ushbu ko‘nikma allaqachon profilingizga qo‘shilgan.");
      return;
    }

    setSkillsErrorMsg(null);
    setMySkills((prev) => [
      ...prev,
      {
        skill_id: catalogItem.id,
        level: selectedSkillLevel,
        code: catalogItem.code,
        name_uz: catalogItem.name_uz,
        name_ru: catalogItem.name_ru,
        active: true,
      },
    ]);
  };

  // Handle Remove Skill from list
  const handleRemoveSkill = (skillId: string) => {
    setMySkills((prev) => prev.filter((s) => s.skill_id !== skillId));
  };

  // Handle Save Skills to Backend (API-032)
  const handleSaveSkills = async () => {
    setIsSavingSkills(true);
    setSkillsSuccessMsg(null);
    setSkillsErrorMsg(null);

    try {
      const skillsPayload = mySkills.map((s) => ({
        skill_id: s.skill_id,
        level: s.level,
      }));

      // Find any removed skills
      const initialSkillIds = (profile?.skills || []).map((s) => s.skill_id);
      const currentSkillIds = new Set(mySkills.map((s) => s.skill_id));
      const removedIds = initialSkillIds.filter((id) => !currentSkillIds.has(id));

      await updateCandidateSkills({
        skills: skillsPayload,
        remove_skill_ids: removedIds,
      });

      setSkillsSuccessMsg("Ko‘nikmalar ro‘yxati muvaffaqiyatli yangilandi.");
      await loadProfileData();
    } catch (err: unknown) {
      setSkillsErrorMsg(err instanceof Error ? err.message : "Ko‘nikmalarni saqlashda xatolik yuz berdi");
    } finally {
      setIsSavingSkills(false);
    }
  };

  // Availability Helpers
  const addAvailabilityRule = (weekday: number) => {
    setRules((prev) => [
      ...prev,
      {
        weekday,
        start_minute: 540, // 09:00
        end_minute: 1080, // 18:00
        timezone: "Asia/Tashkent",
      },
    ]);
  };

  const removeAvailabilityRule = (index: number) => {
    setRules((prev) => prev.filter((_, idx) => idx !== index));
  };

  const updateRuleTimes = (index: number, startStr: string, endStr: string) => {
    const sm = timeStringToMinutes(startStr);
    const em = timeStringToMinutes(endStr);
    setRules((prev) =>
      prev.map((r, idx) => (idx === index ? { ...r, start_minute: sm, end_minute: em } : r))
    );
  };

  // Handle Save Availability to Backend (API-028)
  const handleSaveAvailability = async () => {
    setIsSavingAvailability(true);
    setAvailSuccessMsg(null);
    setAvailErrorMsg(null);

    // Validate rules
    for (const r of rules) {
      if (r.start_minute >= r.end_minute) {
        setAvailErrorMsg("Boshlanish vaqti tugash vaqtidan oldin bo'lishi shart.");
        setIsSavingAvailability(false);
        return;
      }
      const dur = r.end_minute - r.start_minute;
      if (dur > 480) {
        setAvailErrorMsg(
          "O'zR MK 118-moddasi: Bir kunlik ish/amaliyot davomiyligi 8 soatdan (480 daqiqa) oshmasligi shart."
        );
        setIsSavingAvailability(false);
        return;
      }
    }

    try {
      await saveCandidateAvailability(rules);
      setAvailSuccessMsg("Haftalik ish va dars jadvali muvaffaqiyatli saqlandi.");
      await loadAvailabilityData();
    } catch (err: unknown) {
      setAvailErrorMsg(err instanceof Error ? err.message : "Jadvalni saqlashda xatolik yuz berdi");
    } finally {
      setIsSavingAvailability(false);
    }
  };

  // Filter catalog skills by search
  const filteredCatalogSkills = useMemo(() => {
    if (!skillSearchQuery.trim()) return catalogSkills;
    const q = skillSearchQuery.toLowerCase();
    return catalogSkills.filter(
      (s) =>
        s.name_uz.toLowerCase().includes(q) ||
        s.code.toLowerCase().includes(q) ||
        s.name_ru.toLowerCase().includes(q)
    );
  }, [catalogSkills, skillSearchQuery]);

  return (
    <main className="max-w-[1440px] w-full mx-auto px-4 md:px-8 py-6 flex flex-col gap-6">
      {/* HEADER SECTION */}
      <section className="w-full bg-[#121214] border border-white/[0.08] rounded-xl p-5 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                Nomzod Kabineti
              </span>
              <span className="text-zinc-500 text-xs">• API-026 / API-028 / API-032 / API-035</span>
              {currentUser ? (
                <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  Faol: {currentUser.user_id.slice(0, 8)}... ({currentUser.roles.join(", ")})
                </span>
              ) : (
                <span className="text-[11px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                  Avtorizatsiyadan o‘tilmagan
                </span>
              )}
            </div>
            <h1 className="font-heading text-lg md:text-xl font-bold text-white tracking-tight">
              Nomzod Profili va Vaqt Taqsimoti Markazi
            </h1>
            <p className="text-xs text-zinc-400">
              Kasbiy rezyume ma'lumotlari, tasdiqlangan ko‘nikmalar katalogi va O‘zR MK 118-moddasi bo‘yicha haftalik grafik boshqaruvi.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {isAuthLoading ? (
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Yuklanmoqda...</span>
              </div>
            ) : currentUser ? (
              <button
                type="button"
                onClick={handleLogout}
                className="px-3.5 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-rose-300 hover:text-rose-200 transition-all flex items-center gap-1.5"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Chiqish</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setIsLoginModalOpen(true)}
                className="px-3.5 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-primary/20"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Nomzod sifatida kirish</span>
              </button>
            )}
          </div>
        </div>
      </section>

      {/* LOGIN REQUIRED GATE */}
      {!currentUser && !isAuthLoading && (
        <section className="w-full bg-[#121214] border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center text-center gap-3">
          <div className="w-12 h-12 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary mb-1">
            <User className="w-6 h-6" />
          </div>
          <h2 className="text-base font-bold text-white">Profilni boshqarish uchun tizimga kiring</h2>
          <p className="text-xs text-zinc-400 max-w-md">
            Shaxsiy professional rezyume, ko‘nikmalar ro‘yxati va haftalik bo‘sh vaqt jadvalini sozlash uchun hisobingizga kiring.
          </p>
          <button
            type="button"
            onClick={() => setIsLoginModalOpen(true)}
            className="mt-2 px-4 py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all shadow-md shadow-primary/20"
          >
            Kirish oynasini ochish
          </button>
        </section>
      )}

      {/* AUTHENTICATED TABS & PANELS */}
      {currentUser && (
        <div className="flex flex-col gap-6">
          {/* TAB NAVIGATION */}
          <div className="flex border-b border-white/[0.08] gap-1 overflow-x-auto pb-px">
            <button
              type="button"
              onClick={() => setActiveTab("PROFILE")}
              className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "PROFILE"
                  ? "border-primary text-white bg-primary/5"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <User className="w-4 h-4 text-primary" />
              <span>Kasbiy Profil (API-026)</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("SKILLS")}
              className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "SKILLS"
                  ? "border-primary text-white bg-primary/5"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Sparkles className="w-4 h-4 text-emerald-400" />
              <span>Ko‘nikmalar Katalogi (API-032)</span>
              {mySkills.length > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-400">
                  {mySkills.length}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("AVAILABILITY")}
              className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "AVAILABILITY"
                  ? "border-primary text-white bg-primary/5"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Calendar className="w-4 h-4 text-amber-400" />
              <span>Dars & Ish Jadvali (API-028 / API-035)</span>
              {rules.length > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-400">
                  {rules.length} ta qoida
                </span>
              )}
            </button>
          </div>

          {/* TAB 1: PROFILE TAB */}
          {activeTab === "PROFILE" && (
            <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-6 flex flex-col gap-5 shadow-sm max-w-4xl">
              <div>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <User className="w-4 h-4 text-primary" />
                  <span>Asosiy Rezyume Ma'lumotlari</span>
                </h3>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Ish beruvchilar va sun'iy neyro-matching tizimi uchun asosiy mutaxassislik ko'rsatkichlaringiz.
                </p>
              </div>

              {profileSuccessMsg && (
                <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                  <span>{profileSuccessMsg}</span>
                </div>
              )}

              {profileErrorMsg && (
                <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{profileErrorMsg}</span>
                </div>
              )}

              {isLoadingProfile ? (
                <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-400">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  <span className="text-xs">Profil ma'lumotlari yuklanmoqda...</span>
                </div>
              ) : (
                <form onSubmit={handleSaveProfile} className="flex flex-col gap-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-zinc-300">
                        Kasbiy Sarlavha (Headline) *
                      </label>
                      <input
                        type="text"
                        value={profileHeadline}
                        onChange={(e) => setProfileHeadline(e.target.value)}
                        placeholder="Masalan: Full-stack Python & React Dasturchi"
                        className="w-full px-3.5 py-2.5 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50"
                        required
                        maxLength={200}
                      />
                      <span className="text-[11px] text-zinc-500">Maksimal 200 ta belgi</span>
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-zinc-300">Hudud / Viloyat *</label>
                      <select
                        value={profileRegion}
                        onChange={(e) => setProfileRegion(e.target.value)}
                        className="w-full px-3.5 py-2.5 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:outline-none focus:border-primary/50"
                      >
                        {UZBEKISTAN_REGIONS.map((r) => (
                          <option key={r} value={r} className="bg-surface text-white">
                            {r}
                          </option>
                        ))}
                      </select>
                      <span className="text-[11px] text-zinc-500">Amaliyot yoki ish hududi</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-zinc-300">
                        Umumiy Ish Tajribasi (oylar hisobida)
                      </label>
                      <div className="flex items-center gap-3">
                        <input
                          type="number"
                          min={0}
                          max={1200}
                          value={profileExpMonths}
                          onChange={(e) => setProfileExpMonths(Number(e.target.value))}
                          className="w-32 px-3.5 py-2.5 rounded-lg bg-surface border border-white/[0.08] text-xs text-white font-mono focus:outline-none focus:border-primary/50"
                        />
                        <span className="text-xs text-zinc-400">
                          {Math.floor(profileExpMonths / 12)} yil {profileExpMonths % 12} oy
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-zinc-300">Rezyume / CV Holati</label>
                      <div className="flex items-center gap-2 p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                        <FileText className="w-4 h-4 text-primary" />
                        <span className="text-xs text-zinc-300">
                          {profile?.cv_file_id
                            ? `Fayl biriktirilgan (ID: ${profile.cv_file_id.slice(0, 8)}...)`
                            : "Hozircha CV fayli biriktirilmagan"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-zinc-300">
                      O‘zingiz haqingizda (Bio / Tavsif)
                    </label>
                    <textarea
                      rows={4}
                      value={profileBio}
                      onChange={(e) => setProfileBio(e.target.value)}
                      placeholder="Loyihalaringiz, qiziqishlaringiz va amaliyotdan kutayotgan maqsadlaringiz haqida qisqacha yozing..."
                      className="w-full px-3.5 py-2.5 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50 resize-y"
                      maxLength={5000}
                    />
                    <span className="text-[11px] text-zinc-500">Maksimal 5000 ta belgi</span>
                  </div>

                  <div className="pt-2 flex justify-end">
                    <button
                      type="submit"
                      disabled={isSavingProfile}
                      className="px-5 py-2.5 rounded-lg bg-primary hover:bg-primary/90 disabled:opacity-50 text-xs font-semibold text-white transition-all flex items-center gap-2 shadow-md shadow-primary/20"
                    >
                      {isSavingProfile ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Saqlanmoqda...</span>
                        </>
                      ) : (
                        <>
                          <Save className="w-3.5 h-3.5" />
                          <span>Profilni Saqlash (API-026)</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* TAB 2: SKILLS TAB */}
          {activeTab === "SKILLS" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* LEFT 2 COLS: MY ACTIVE SKILLS */}
              <div className="lg:col-span-2 bg-[#121214] border border-white/[0.08] rounded-xl p-5 flex flex-col gap-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-emerald-400" />
                      <span>Tanlangan Ko‘nikmalarim ({mySkills.length} ta)</span>
                    </h3>
                    <p className="text-xs text-zinc-400">
                      Ushbu ko‘nikmalar asosida bo‘sh ish o‘rinlari bilan neyro-moslik darajasi hisoblanadi.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleSaveSkills}
                    disabled={isSavingSkills}
                    className="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-sm shadow-emerald-500/20"
                  >
                    {isSavingSkills ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Save className="w-3.5 h-3.5" />
                    )}
                    <span>Saqlash (API-032)</span>
                  </button>
                </div>

                {skillsSuccessMsg && (
                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                    <span>{skillsSuccessMsg}</span>
                  </div>
                )}

                {skillsErrorMsg && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>{skillsErrorMsg}</span>
                  </div>
                )}

                {mySkills.length === 0 ? (
                  <div className="py-12 border border-dashed border-white/[0.08] rounded-lg flex flex-col items-center justify-center gap-2 text-center">
                    <Sparkles className="w-6 h-6 text-zinc-500 mb-1" />
                    <span className="text-xs font-semibold text-zinc-300">
                      Hali hech qanday ko‘nikma qo‘shilmagan
                    </span>
                    <span className="text-[11px] text-zinc-500 max-w-sm">
                      O‘ng tomondagi katalogdan texnologiya va darajangizni tanlab, "Qo‘shish" tugmasini bosing.
                    </span>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {mySkills.map((s) => (
                      <div
                        key={s.skill_id}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface border border-white/[0.08] hover:border-white/20 transition-all text-xs"
                      >
                        <span className="font-semibold text-white">{s.name_uz || s.code}</span>
                        <span
                          className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                            s.level === "ADVANCED"
                              ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                              : s.level === "INTERMEDIATE"
                              ? "bg-primary/20 text-blue-300 border border-primary/30"
                              : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          }`}
                        >
                          {s.level}
                        </span>
                        {s.verified && (
                          <span
                            title="Universitet yoki sertifikat bilan tasdiqlangan"
                            className="text-emerald-400 flex items-center"
                          >
                            <ShieldCheck className="w-3.5 h-3.5" />
                          </span>
                        )}
                        <button
                          type="button"
                          onClick={() => handleRemoveSkill(s.skill_id)}
                          className="text-zinc-500 hover:text-rose-400 transition-colors ml-1"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* RIGHT 1 COL: ADD FROM CATALOG */}
              <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-5 flex flex-col gap-4 shadow-sm">
                <div>
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Plus className="w-4 h-4 text-primary" />
                    <span>Katalogdan Qo‘shish</span>
                  </h3>
                  <p className="text-[11px] text-zinc-400 mt-0.5">
                    Platformada tasdiqlangan rasmiy texnologiyalar.
                  </p>
                </div>

                {/* SEARCH CATALOG */}
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-3 top-3" />
                  <input
                    type="text"
                    value={skillSearchQuery}
                    onChange={(e) => {
                      setSkillSearchQuery(e.target.value);
                      loadCatalog(e.target.value);
                    }}
                    placeholder="Qidirish (Python, React, SQL...)"
                    className="w-full pl-8 pr-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] font-semibold text-zinc-400">Ko‘nikmani Tanlang</label>
                  <select
                    value={selectedCatalogSkillId}
                    onChange={(e) => setSelectedCatalogSkillId(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:outline-none focus:border-primary/50"
                  >
                    {filteredCatalogSkills.map((c) => (
                      <option key={c.id} value={c.id} className="bg-surface text-white">
                        {c.name_uz} ({c.code})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] font-semibold text-zinc-400">Mahorat Darajasi</label>
                  <select
                    value={selectedSkillLevel}
                    onChange={(e) => setSelectedSkillLevel(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:outline-none focus:border-primary/50"
                  >
                    <option value="BEGINNER" className="bg-surface text-white">
                      BEGINNER — Boshlang‘ich
                    </option>
                    <option value="INTERMEDIATE" className="bg-surface text-white">
                      INTERMEDIATE — O‘rta (Mustaqil ishlay oladi)
                    </option>
                    <option value="ADVANCED" className="bg-surface text-white">
                      ADVANCED — Yuqori (Katta amaliy tajriba)
                    </option>
                  </select>
                </div>

                <button
                  type="button"
                  onClick={handleAddSkill}
                  className="w-full mt-2 px-3.5 py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center justify-center gap-2 shadow-md shadow-primary/20"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Ro‘yxatga qo‘shish</span>
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: AVAILABILITY TAB */}
          {activeTab === "AVAILABILITY" && (
            <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-6 flex flex-col gap-5 shadow-sm max-w-4xl">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-amber-400" />
                    <span>Haftalik Dars va Ish Oralig‘i Grafigi</span>
                  </h3>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    O‘zR MK 118-moddasi talabi: dars vaqti bilan amaliyot/ish soatlari to‘qnashmasligi shart.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={handleSaveAvailability}
                  disabled={isSavingAvailability}
                  className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 disabled:opacity-50 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-primary/20 self-start sm:self-auto"
                >
                  {isSavingAvailability ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Save className="w-3.5 h-3.5" />
                  )}
                  <span>Jadvalni Saqlash (API-028)</span>
                </button>
              </div>

              {availSuccessMsg && (
                <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                  <span>{availSuccessMsg}</span>
                </div>
              )}

              {availErrorMsg && (
                <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{availErrorMsg}</span>
                </div>
              )}

              {isLoadingAvailability ? (
                <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-400">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  <span className="text-xs">Jadval ma'lumotlari yuklanmoqda...</span>
                </div>
              ) : (
                <div className="flex flex-col gap-4">
                  {WEEKDAY_NAMES.map((day) => {
                    const dayRules = rules.map((r, idx) => ({ ...r, originalIndex: idx })).filter((r) => r.weekday === day.id);
                    const totalDayMinutes = dayRules.reduce((sum, r) => sum + (r.end_minute - r.start_minute), 0);
                    const isLimitExceeded = totalDayMinutes > 480;

                    return (
                      <div
                        key={day.id}
                        className="p-4 rounded-xl bg-surface border border-white/[0.06] flex flex-col gap-3"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-white">{day.name}</span>
                            <span
                              className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                                totalDayMinutes === 0
                                  ? "bg-zinc-800 text-zinc-400"
                                  : isLimitExceeded
                                  ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                                  : "bg-primary/20 text-blue-300 border border-primary/30"
                              }`}
                            >
                              {totalDayMinutes > 0
                                ? `${Math.floor(totalDayMinutes / 60)} soat ${totalDayMinutes % 60} daqiqa`
                                : "Dam olish kuni"}
                            </span>
                          </div>

                          <button
                            type="button"
                            onClick={() => addAvailabilityRule(day.id)}
                            className="px-2.5 py-1 rounded bg-white/[0.04] hover:bg-white/[0.08] text-[11px] font-semibold text-primary flex items-center gap-1 transition-all"
                          >
                            <Plus className="w-3 h-3" />
                            <span>Vaqt oralig‘i qo‘shish</span>
                          </button>
                        </div>

                        {dayRules.length === 0 ? (
                          <span className="text-[11px] text-zinc-500 italic">
                            Ushbu kunda ishlash rejalashtirilmagan.
                          </span>
                        ) : (
                          <div className="flex flex-col gap-2">
                            {dayRules.map((r) => (
                              <div
                                key={r.originalIndex}
                                className="flex flex-wrap items-center gap-3 p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                              >
                                <div className="flex items-center gap-1.5 text-xs text-zinc-300">
                                  <Clock className="w-3.5 h-3.5 text-primary" />
                                  <span>Boshlanish:</span>
                                  <input
                                    type="time"
                                    value={minutesToTimeString(r.start_minute)}
                                    onChange={(e) =>
                                      updateRuleTimes(
                                        r.originalIndex,
                                        e.target.value,
                                        minutesToTimeString(r.end_minute)
                                      )
                                    }
                                    className="px-2 py-1 rounded bg-surface border border-white/[0.08] text-xs text-white font-mono focus:outline-none"
                                  />
                                </div>

                                <div className="flex items-center gap-1.5 text-xs text-zinc-300">
                                  <span>Tugash:</span>
                                  <input
                                    type="time"
                                    value={minutesToTimeString(r.end_minute)}
                                    onChange={(e) =>
                                      updateRuleTimes(
                                        r.originalIndex,
                                        minutesToTimeString(r.start_minute),
                                        e.target.value
                                      )
                                    }
                                    className="px-2 py-1 rounded bg-surface border border-white/[0.08] text-xs text-white font-mono focus:outline-none"
                                  />
                                </div>

                                <span className="text-[11px] font-mono text-zinc-400">
                                  ({r.end_minute - r.start_minute} daqiqa)
                                </span>

                                <button
                                  type="button"
                                  onClick={() => removeAvailabilityRule(r.originalIndex)}
                                  className="ml-auto text-zinc-500 hover:text-rose-400 transition-colors"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* AUTH MODAL */}
      <AuthModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onSuccess={(user) => {
          setCurrentUser(user);
          loadProfileData();
          loadCatalog();
          loadAvailabilityData();
        }}
      />
    </main>
  );
}

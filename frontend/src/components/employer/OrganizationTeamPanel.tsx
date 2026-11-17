"use client";

import { useId, useState } from "react";
import { AlertCircle, Check, CheckCircle2, Copy, Loader2, RefreshCw, Send, UserMinus, Users, X } from "lucide-react";
import { useAsyncData } from "@/lib/useAsyncData";
import {
  ROLE_HINTS,
  ROLE_LABELS,
  approveJoin,
  createInvitation,
  describeOrgError,
  fetchTeam,
  invitationLink,
  normalizeDestination,
  removeMember,
  revokeInvitation,
  type OrgRole,
  type TeamMember,
} from "@/lib/orgTeam";

const fmt = (iso?: string | null) => (iso ? new Date(iso).toLocaleDateString("uz-UZ") : "");
const INVITE_ROLES: Exclude<OrgRole, "OWNER">[] = ["HR", "MENTOR", "HOST_COORDINATOR", "BILLING"];

function RoleChips({ roles }: { roles: string[] }) {
  return (
    <>
      {roles.map((r) => (
        <span key={r} className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 text-xs font-semibold text-emerald-700 dark:text-emerald-300">
          {ROLE_LABELS[r] ?? r}
        </span>
      ))}
    </>
  );
}

/**
 * The company's main (OWNER) account manages its people: invite staff with a
 * shareable 24-hour link, approve join requests, see names and roles, and
 * remove access with a reason.
 */
export default function OrganizationTeamPanel({ orgId }: { orgId: string | null }) {
  const ids = useId();
  const q = useAsyncData(orgId ? `team:${orgId}` : null, () => fetchTeam(orgId as string));
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const [dest, setDest] = useState("");
  const [role, setRole] = useState<Exclude<OrgRole, "OWNER">>("HR");
  const [link, setLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const [removing, setRemoving] = useState<{ kind: "member" | "invite"; id: string } | null>(null);
  const [reason, setReason] = useState("");

  if (!orgId) return null;
  const data = q.data;
  const error = actionError ?? (q.error ? describeOrgError(q.error) : null);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    setActionError(null);
    setNotice(null);
    try {
      await fn();
      await q.reload();
    } catch (err) {
      setActionError(describeOrgError(err));
    } finally {
      setBusy(null);
    }
  };

  const invite = (e: React.FormEvent) => {
    e.preventDefault();
    const { channel, destination } = normalizeDestination(dest);
    void run("invite", async () => {
      const res = await createInvitation(orgId, channel, destination, role);
      setLink(invitationLink(res.token));
      setCopied(false);
      setDest("");
    });
  };

  const copy = async () => {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  const confirmRemove = () => {
    if (!removing) return;
    const target = removing;
    void run("remove", async () => {
      if (target.kind === "member") await removeMember(orgId, target.id, reason.trim());
      else await revokeInvitation(orgId, target.id, reason.trim());
      setNotice(target.kind === "member" ? "Xodimning korxonadagi ruxsati bekor qilindi." : "Taklif bekor qilindi.");
      setRemoving(null);
      setReason("");
    });
  };

  const removeBox = (id: string, kind: "member" | "invite") =>
    removing?.id === id && removing.kind === kind ? (
      <div className="flex flex-col sm:flex-row gap-2 pt-1">
        <label htmlFor={`${ids}-reason`} className="sr-only">
          Sabab
        </label>
        <input
          id={`${ids}-reason`}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Sabab (kamida 15 belgi), masalan: korxonadan ishdan bo‘shadi"
          className="skeuo-input min-w-0 flex-1 rounded-xl px-3.5 py-2 text-sm"
          autoFocus
        />
        <div className="flex gap-2">
          <button type="button" onClick={() => setRemoving(null)} className="skeuo-btn-secondary rounded-xl px-3 py-2 text-xs">
            Yo‘q
          </button>
          <button
            type="button"
            disabled={reason.trim().length < 15 || busy === "remove"}
            onClick={confirmRemove}
            className="rounded-xl bg-rose-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
          >
            Tasdiqlash
          </button>
        </div>
      </div>
    ) : null;

  const member = (m: TeamMember) => (
    <li key={m.membership_id} className="rounded-2xl skeuo-well p-4 flex flex-col gap-2">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="min-w-0 flex flex-wrap items-center gap-2">
          <span className="font-semibold text-[var(--fb-ink)]">{m.display_name}</span>
          {m.is_self && <span className="text-xs text-[var(--fb-ink-muted)]">(siz)</span>}
          {m.status === "ACTIVE" ? (
            <RoleChips roles={m.roles} />
          ) : (
            <span className="rounded-full border border-zinc-500/20 bg-zinc-500/10 px-2 py-0.5 text-xs text-[var(--fb-ink-secondary)]">
              {m.status === "REVOKED" ? "Chiqarilgan" : m.status === "PENDING_VERIFICATION" ? "Tekshiruvda" : m.status}
            </span>
          )}
        </div>
        {!m.is_self && m.status === "ACTIVE" && !m.roles.includes("OWNER") && (
          <button
            type="button"
            onClick={() => {
              setRemoving({ kind: "member", id: m.membership_id });
              setReason("");
            }}
            className="skeuo-btn-secondary self-start rounded-xl px-3 py-1.5 text-xs"
          >
            <UserMinus className="h-3.5 w-3.5" aria-hidden="true" />
            Chiqarish
          </button>
        )}
      </div>
      <div className="text-xs text-[var(--fb-ink-muted)]">Qo‘shilgan: {fmt(m.accepted_at || m.created_at)}</div>
      {removeBox(m.membership_id, "member")}
    </li>
  );

  const activeMembers = data?.members.filter((m) => m.status !== "REVOKED") ?? [];
  const pendingOrg = data && data.organization.status !== "VERIFIED";

  return (
    <section className="skeuo-card rounded-[24px] p-5 sm:p-6 flex flex-col gap-5" aria-labelledby={`${ids}-title`}>
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 id={`${ids}-title`} className="font-heading text-lg font-bold text-[var(--fb-ink)] flex items-center gap-2">
            <Users className="h-5 w-5 text-emerald-600 dark:text-emerald-300" aria-hidden="true" />
            Jamoa
          </h2>
          <p className="text-sm text-[var(--fb-ink-secondary)] max-w-2xl">
            Siz korxonaning asosiy akkauntisiz. Xodimlarni taklif qiling, qo‘shilish so‘rovlarini tasdiqlang va kerak bo‘lsa ruxsatni bekor qiling.
          </p>
        </div>
        <button type="button" onClick={() => void q.reload()} disabled={q.isLoading} aria-label="Yangilash" className="skeuo-btn-secondary rounded-xl px-3 py-2 text-xs shrink-0">
          <RefreshCw className={`h-3.5 w-3.5 ${q.isLoading ? "animate-spin" : ""}`} aria-hidden="true" />
        </button>
      </div>

      {pendingOrg && (
        <div className="flex items-start gap-2.5 rounded-2xl border border-amber-500/25 bg-amber-500/10 p-3.5 text-sm text-amber-800 dark:text-amber-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          Korxona hali tekshiruvda. Tasdiqlangach, xodim taklif qilish va so‘rovlarni tasdiqlash ochiladi.
        </div>
      )}
      {error && (
        <div role="alert" className="flex items-start gap-2.5 rounded-2xl border border-rose-500/25 bg-rose-500/10 p-3.5 text-sm text-rose-700 dark:text-rose-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {error}
        </div>
      )}
      {notice && (
        <div className="flex items-start gap-2.5 rounded-2xl border border-emerald-500/25 bg-emerald-500/10 p-3.5 text-sm text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {notice}
        </div>
      )}

      {/* Invite */}
      <form onSubmit={invite} className="rounded-2xl skeuo-well p-4 grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,14rem)_auto] sm:items-end">
        <div className="min-w-0">
          <label htmlFor={`${ids}-dest`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
            Xodimning telefoni yoki pochtasi
          </label>
          <input
            id={`${ids}-dest`}
            value={dest}
            onChange={(e) => setDest(e.target.value)}
            placeholder="+998 90 123 45 67 yoki hr@korxona.uz"
            autoComplete="off"
            disabled={Boolean(pendingOrg)}
            className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm"
          />
        </div>
        <div className="min-w-0">
          <label htmlFor={`${ids}-role`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
            Rol
          </label>
          <select
            id={`${ids}-role`}
            value={role}
            onChange={(e) => setRole(e.target.value as Exclude<OrgRole, "OWNER">)}
            disabled={Boolean(pendingOrg)}
            className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm"
          >
            {INVITE_ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={Boolean(pendingOrg) || dest.trim().length < 5 || busy === "invite"}
          data-tone="emerald"
          className="skeuo-btn-tone rounded-xl px-4 py-2.5 text-sm disabled:opacity-50"
        >
          {busy === "invite" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Send className="h-4 w-4" aria-hidden="true" />}
          Taklif havolasi
        </button>
        <p className="sm:col-span-3 text-xs text-[var(--fb-ink-muted)]">{ROLE_HINTS[role]}</p>
      </form>

      {link && (
        <div className="rounded-2xl border border-emerald-500/25 bg-emerald-500/10 p-4 flex flex-col gap-2">
          <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-200">
            Havolani xodimga Telegram yoki SMS orqali yuboring. U 24 soat amal qiladi va faqat shu telefon/pochta egasi qabul qila oladi.
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            <input readOnly value={link} aria-label="Taklif havolasi" className="skeuo-input min-w-0 flex-1 rounded-xl px-3 py-2 font-mono text-xs" onFocus={(e) => e.currentTarget.select()} />
            <button type="button" onClick={() => void copy()} className="skeuo-btn-secondary rounded-xl px-3 py-2 text-xs">
              {copied ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}
              {copied ? "Nusxalandi" : "Nusxalash"}
            </button>
            <button type="button" onClick={() => setLink(null)} aria-label="Yopish" className="skeuo-btn-secondary rounded-xl px-3 py-2 text-xs">
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
        </div>
      )}

      {q.isLoading && !data ? (
        <div className="flex items-center gap-2 text-sm text-[var(--fb-ink-secondary)]">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Yuklanmoqda…
        </div>
      ) : data ? (
        <>
          {data.join_requests.length > 0 && (
            <div className="flex flex-col gap-2.5">
              <h3 className="text-sm font-bold text-[var(--fb-ink)]">Qo‘shilish so‘rovlari ({data.join_requests.length})</h3>
              <ul className="flex flex-col gap-2.5">
                {data.join_requests.map((r) => (
                  <li key={r.membership_id} className="rounded-2xl skeuo-well p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="font-semibold text-[var(--fb-ink)]">{r.display_name}</div>
                      <div className="text-xs text-[var(--fb-ink-muted)]">
                        So‘ralgan rol: {r.requested_role ? ROLE_LABELS[r.requested_role] ?? r.requested_role : "—"} · {fmt(r.created_at)}
                      </div>
                      {removeBox(r.membership_id, "member")}
                    </div>
                    {removing?.id !== r.membership_id && (
                      <div className="flex gap-2 self-start">
                        <button
                          type="button"
                          onClick={() => {
                            setRemoving({ kind: "member", id: r.membership_id });
                            setReason("");
                          }}
                          className="skeuo-btn-secondary rounded-xl px-3 py-1.5 text-xs"
                        >
                          Rad etish
                        </button>
                        <button
                          type="button"
                          disabled={busy === r.membership_id}
                          onClick={() =>
                            void run(r.membership_id, async () => {
                              await approveJoin(orgId, r.membership_id);
                              setNotice(`${r.display_name} jamoaga qo‘shildi.`);
                            })
                          }
                          data-tone="emerald"
                          className="skeuo-btn-tone rounded-xl px-3 py-1.5 text-xs disabled:opacity-50"
                        >
                          Tasdiqlash
                        </button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-col gap-2.5">
            <h3 className="text-sm font-bold text-[var(--fb-ink)]">Xodimlar ({activeMembers.length})</h3>
            <ul className="flex flex-col gap-2.5">{activeMembers.map(member)}</ul>
          </div>

          {data.invitations.length > 0 && (
            <div className="flex flex-col gap-2.5">
              <h3 className="text-sm font-bold text-[var(--fb-ink)]">Javob kutilayotgan takliflar</h3>
              <ul className="flex flex-col gap-2.5">
                {data.invitations.map((inv) => (
                  <li key={inv.id} className="rounded-2xl skeuo-well p-4 flex flex-col gap-2">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="text-sm text-[var(--fb-ink)]">
                        {inv.role_code ? ROLE_LABELS[inv.role_code] ?? inv.role_code : "Rol"} ·{" "}
                        <span className="text-[var(--fb-ink-muted)]">
                          {inv.channel === "EMAIL" ? "pochta" : "telefon"} · {fmt(inv.expires_at)} gacha
                        </span>
                      </div>
                      {removing?.id !== inv.id && (
                        <button
                          type="button"
                          onClick={() => {
                            setRemoving({ kind: "invite", id: inv.id });
                            setReason("");
                          }}
                          className="skeuo-btn-secondary self-start rounded-xl px-3 py-1.5 text-xs"
                        >
                          Bekor qilish
                        </button>
                      )}
                    </div>
                    {removeBox(inv.id, "invite")}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      ) : null}
    </section>
  );
}

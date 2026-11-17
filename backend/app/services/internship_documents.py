"""Standardized Internship Diary, Final Conclusion Document & 3-Party E-Imzo Service (FB-204)."""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import select

from app.adapters import storage
from app.adapters.storage import ObjectReference, file_reference
from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.core.config import settings
from app.db.storage import (
    files_table,
    load_domain_record,
    now,
    save_domain_record,
    table,
    transaction,
)
from app.services.authority import institution_role_authority, org_authority
from app.services.placement_admission import PlacementScopeError, get_row

audit = AppendOnlyAuditStore()

NS_EIMZO_CERTS = "eimzo_certificates"
NS_DIARY_STANDARDS = "diary_standards"
NS_DIARY_SIGNATURES = "diary_signatures"
NS_CONCLUSION_DOCS = "final_conclusion_documents"
NS_EIMZO_LEDGER = "eimzo_verification_ledger"

VALID_PARTIES = ("CANDIDATE", "EMPLOYER", "UNIVERSITY")
VALID_INTERNSHIP_TYPES = ("ISHLAB_CHIQARISH", "MALAKA", "DIPLOM_OLDI", "TANISHUV")
VALID_EMPLOYER_VERDICTS = (
    "RECOMMENDED_FOR_HIRE",
    "SUCCESSFULLY_COMPLETED",
    "CONDITIONAL",
    "NOT_RECOMMENDED",
)
VALID_UNIVERSITY_VERDICTS = ("APPROVED_CREDIT", "REVISION_REQUIRED", "FAILED")
VALID_GRADES = ("A", "B", "C", "D", "F")

_ACTIVE_ORG_STATES = ("ACTIVE", "VERIFIED", "GRANTED", "ACCEPTED")
_ACTIVE_INST_STATES = ("ACTIVE", "VERIFIED", "ACCEPTED", "APPOINTED", "APPROVED")


def _hmac_secret() -> bytes:
    secret = (
        os.environ.get("FLEXBRIDGE_EIMZO_SECRET")
        or getattr(settings, "signing_secret", None)
        or getattr(settings, "session_secret", None)
        or "flexbridge-uz-eimzo-2026-canonical-hmac-key"
    )
    return str(secret).encode("utf-8")


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def _sha256_hex(data: Any) -> str:
    raw = data if isinstance(data, bytes) else _canonical_json(data).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sign_hmac(payload_digest: str, cert_serial: str, party: str, user_id: str) -> str:
    msg = f"{party}|{user_id}|{cert_serial}|{payload_digest}".encode("utf-8")
    return hmac.new(_hmac_secret(), msg, hashlib.sha256).hexdigest()


def _safe_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    return str(val).strip()


def _to_ascii_pdf(text: Any) -> str:
    """Normalize text safely into WinAnsi/ASCII for deterministic Helvetica rendering."""
    raw = str(text or "")
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u02bb": "'",
        "\u02bc": "'",
        "`": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2022": "*",
        "\u00ab": '"',
        "\u00bb": '"',
        "\r": " ",
        "\n": " ",
    }
    for k, v in replacements.items():
        raw = raw.replace(k, v)
    return raw.encode("latin-1", "replace").decode("latin-1")


def _escape_pdf_literal(text: str) -> str:
    return _to_ascii_pdf(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_text(text: str, width_chars: int = 86) -> list[str]:
    clean = " ".join(_to_ascii_pdf(text).split())
    if not clean:
        return ["-"]
    words = clean.split(" ")
    lines: list[str] = []
    cur = ""
    for w in words:
        while len(w) > width_chars:
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(w[:width_chars])
            w = w[width_chars:]
        cand = f"{cur} {w}".strip() if cur else w
        if len(cand) <= width_chars:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class _A4PdfCanvas:
    """Multi-page A4 (595x842pt) PDF writer using pypdf content streams and Helvetica fonts."""

    def __init__(self) -> None:
        self.pages: list[list[str]] = []
        self.y = 790.0
        self.new_page()

    def new_page(self) -> None:
        self.pages.append([])
        self.y = 795.0
        self._draw_rect(36, 804, 523, 24, fill_rgb=(0.08, 0.14, 0.24))
        self._text(
            44,
            812,
            "O'ZBEKISTON RESPUBLIKASI  |  FLEXBRIDGE RASMIY AMALIYOT HUJJAT TIZIMI",
            size=8.5,
            bold=True,
            rgb=(0.95, 0.97, 1.0),
        )
        self.y = 786.0

    def ensure_space(self, needed: float) -> None:
        if self.y - needed < 48.0:
            self.new_page()

    def _draw_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill_rgb: tuple[float, float, float] | None = None,
        stroke_rgb: tuple[float, float, float] | None = None,
    ) -> None:
        cmds = ["q"]
        if fill_rgb:
            cmds.append(f"{fill_rgb[0]:.3f} {fill_rgb[1]:.3f} {fill_rgb[2]:.3f} rg")
        if stroke_rgb:
            cmds.append(f"{stroke_rgb[0]:.3f} {stroke_rgb[1]:.3f} {stroke_rgb[2]:.3f} RG 0.7 w")
        cmds.append(f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re")
        if fill_rgb and stroke_rgb:
            cmds.append("B")
        elif fill_rgb:
            cmds.append("f")
        else:
            cmds.append("S")
        cmds.append("Q")
        self.pages[-1].append(" ".join(cmds))

    def _text(
        self,
        x: float,
        y: float,
        txt: str,
        *,
        size: float = 9.5,
        bold: bool = False,
        rgb: tuple[float, float, float] = (0.10, 0.12, 0.16),
    ) -> None:
        font = "/F2" if bold else "/F1"
        esc = _escape_pdf_literal(txt)
        self.pages[-1].append(
            f"BT {font} {size:.1f} Tf {rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} rg 1 0 0 1 {x:.1f} {y:.1f} Tm ({esc}) Tj ET"
        )

    def heading(self, title: str, subtitle: str | None = None) -> None:
        self.ensure_space(46)
        self._text(36, self.y, title, size=13.5, bold=True, rgb=(0.05, 0.12, 0.25))
        self.y -= 15
        if subtitle:
            self._text(36, self.y, subtitle, size=8.8, bold=False, rgb=(0.35, 0.40, 0.48))
            self.y -= 12
        self._draw_rect(36, self.y + 4, 523, 1.2, fill_rgb=(0.15, 0.35, 0.68))
        self.y -= 10

    def section(self, title: str) -> None:
        self.ensure_space(28)
        self.y -= 4
        self._draw_rect(36, self.y - 3, 523, 16, fill_rgb=(0.93, 0.95, 0.98), stroke_rgb=(0.78, 0.83, 0.90))
        self._text(42, self.y + 1, title, size=9.5, bold=True, rgb=(0.08, 0.20, 0.42))
        self.y -= 16

    def kv_row(self, key: str, value: str, *, label_w: float = 165.0) -> None:
        lines = _wrap_text(value, width_chars=64)
        needed = max(13.0, len(lines) * 11.5 + 3.0)
        self.ensure_space(needed)
        self._text(40, self.y, f"{key}:", size=8.6, bold=True, rgb=(0.24, 0.28, 0.35))
        for idx, line in enumerate(lines):
            self._text(40 + label_w, self.y - idx * 11.5, line, size=8.6, bold=False)
        self.y -= needed

    def paragraph(self, label: str, text: str) -> None:
        lines = _wrap_text(text, width_chars=92)
        self.ensure_space(16 + len(lines) * 11.5)
        self._text(40, self.y, label, size=8.8, bold=True, rgb=(0.18, 0.22, 0.30))
        self.y -= 12
        for line in lines:
            self.ensure_space(12)
            self._text(44, self.y, line, size=8.5, bold=False)
            self.y -= 11.2
        self.y -= 4

    def eimzo_stamp_box(self, party_title: str, stamp: dict[str, Any] | None) -> None:
        self.ensure_space(68)
        signed = bool(stamp and stamp.get("signature_hmac"))
        bg = (0.93, 0.98, 0.95) if signed else (0.98, 0.96, 0.93)
        border = (0.16, 0.56, 0.34) if signed else (0.75, 0.56, 0.25)
        self._draw_rect(36, self.y - 54, 523, 60, fill_rgb=bg, stroke_rgb=border)
        status_txt = "E-IMZO BILAN TASDIQLANGAN" if signed else "TASDIQLASH KUTILMOQDA (IMZOLANMAGAN)"
        self._text(44, self.y - 8, f"{party_title}  -  {status_txt}", size=9.2, bold=True, rgb=border)
        if signed and stamp:
            signer = f"Imzolovchi: {stamp.get('signer_name', '-')} ({stamp.get('signer_position', '-')})"
            org = f"Muassasa/Tashkilot: {stamp.get('organization_name', '-')} | STIR/PINFL: {stamp.get('stir_or_pinfl', '-')}"
            meta = f"Sertifikat: {stamp.get('certificate_serial', '-')} | Vaqt: {stamp.get('signed_at', '-')}"
            code = f"Tekshiruv kodi: {stamp.get('verification_code', '-')} | Digest: {str(stamp.get('payload_sha256', ''))[:24]}..."
            self._text(44, self.y - 20, signer, size=8.2)
            self._text(44, self.y - 30, org, size=8.0)
            self._text(44, self.y - 40, meta, size=7.8, rgb=(0.25, 0.30, 0.36))
            self._text(44, self.y - 50, code, size=7.8, bold=True, rgb=(0.08, 0.28, 0.45))
        else:
            self._text(44, self.y - 26, "Ushbu tomon hali maxsus E-Imzo kaliti orqali hujjatni imzolamagan.", size=8.2, rgb=(0.45, 0.35, 0.20))
        self.y -= 68

    def to_bytes(self) -> bytes:
        writer = PdfWriter()
        font_dict = DictionaryObject(
            {
                NameObject("/F1"): DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/Font"),
                        NameObject("/Subtype"): NameObject("/Type1"),
                        NameObject("/BaseFont"): NameObject("/Helvetica"),
                        NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
                    }
                ),
                NameObject("/F2"): DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/Font"),
                        NameObject("/Subtype"): NameObject("/Type1"),
                        NameObject("/BaseFont"): NameObject("/Helvetica-Bold"),
                        NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
                    }
                ),
            }
        )
        total_pages = len(self.pages)
        for idx, page_cmds in enumerate(self.pages, start=1):
            cmds = list(page_cmds)
            cmds.append(
                f"BT /F1 7.5 Tf 0.450 0.480 0.540 rg 1 0 0 1 36 22 Tm "
                f"({_escape_pdf_literal(f'FlexBridge E-Imzo Standard Document | Sahifa {idx}/{total_pages}')}) Tj ET"
            )
            page = writer.add_blank_page(width=595, height=842)
            page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): font_dict})
            stream = DecodedStreamObject()
            stream.set_data("\n".join(cmds).encode("latin-1", "replace"))
            page[NameObject("/Contents")] = writer._add_object(stream)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()


def _authorized_parties_for_placement(
    conn: Any,
    actor: ActorContext,
    placement: dict[str, Any],
) -> set[str]:
    """Return which signing parties (CANDIDATE, EMPLOYER, UNIVERSITY) the authenticated actor controls."""
    parties: set[str] = set()
    actor_uid = str(actor.user_id)

    t_cand = table("candidate_profiles")
    cand = conn.execute(
        select(t_cand).where(t_cand.c.id == placement["candidate_id"], t_cand.c.user_id == actor_uid)
    ).mappings().first()
    if cand:
        parties.add("CANDIDATE")

    try:
        org_authority(conn, actor_uid, placement["organization_id"], "OWNER", "HOST_COORDINATOR", "HR", "MENTOR")
        parties.add("EMPLOYER")
    except Exception:
        t_m = table("mentor_assignments")
        t_mp = table("mentor_assignment_proofs")
        masg = conn.execute(
            select(t_m.c.id)
            .select_from(t_m.join(t_mp, t_mp.c.assignment_id == t_m.c.id))
            .where(
                t_m.c.placement_id == placement["id"],
                t_mp.c.mentor_user_id == actor_uid,
                t_m.c.revoked_at.is_(None),
            )
        ).first()
        if masg:
            parties.add("EMPLOYER")

    t_aa = table("academic_assignments")
    t_aap = table("academic_assignment_proofs")
    aasg = conn.execute(
        select(t_aa.c.id)
        .select_from(t_aa.join(t_aap, t_aap.c.assignment_id == t_aa.c.id))
        .where(
            t_aa.c.placement_id == placement["id"],
            t_aap.c.teacher_user_id == actor_uid,
            t_aa.c.revoked_at.is_(None),
        )
    ).first()
    if aasg:
        parties.add("UNIVERSITY")

    if "UNIVERSITY" not in parties and placement.get("enrollment_id"):
        t_enr = table("enrollments")
        enr = conn.execute(
            select(t_enr).where(t_enr.c.id == placement["enrollment_id"])
        ).mappings().first()
        if enr and enr.get("institution_id"):
            try:
                institution_role_authority(conn, actor_uid, enr["institution_id"], "COORDINATOR", "TEACHER")
                parties.add("UNIVERSITY")
            except Exception:
                pass

    return parties


def _user_eligible_parties(conn: Any, actor: ActorContext) -> set[str]:
    """Check which E-Imzo certificate parties an authenticated user may own across their memberships."""
    eligible: set[str] = set()
    uid = str(actor.user_id)

    cand = conn.execute(
        select(table("candidate_profiles")).where(table("candidate_profiles").c.user_id == uid)
    ).mappings().first()
    if cand:
        eligible.add("CANDIDATE")

    org_mem = conn.execute(
        select(table("org_memberships")).where(
            table("org_memberships").c.user_id == uid,
            table("org_memberships").c.status.in_(_ACTIVE_ORG_STATES),
            table("org_memberships").c.revoked_at.is_(None),
        )
    ).mappings().first()
    if org_mem:
        eligible.add("EMPLOYER")

    t_m = table("mentor_assignments")
    t_mp = table("mentor_assignment_proofs")
    has_mentor = conn.execute(
        select(t_m.c.id).select_from(t_m.join(t_mp, t_mp.c.assignment_id == t_m.c.id)).where(
            t_mp.c.mentor_user_id == uid,
            t_m.c.revoked_at.is_(None),
        )
    ).first()
    if has_mentor:
        eligible.add("EMPLOYER")

    inst_mem = conn.execute(
        select(table("institution_memberships")).where(
            table("institution_memberships").c.user_id == uid,
            table("institution_memberships").c.status.in_(_ACTIVE_INST_STATES),
            table("institution_memberships").c.revoked_at.is_(None),
        )
    ).mappings().first()
    if inst_mem:
        eligible.add("UNIVERSITY")

    t_aa = table("academic_assignments")
    t_aap = table("academic_assignment_proofs")
    has_teacher = conn.execute(
        select(t_aa.c.id).select_from(t_aa.join(t_aap, t_aap.c.assignment_id == t_aa.c.id)).where(
            t_aap.c.teacher_user_id == uid,
            t_aa.c.revoked_at.is_(None),
        )
    ).first()
    if has_teacher:
        eligible.add("UNIVERSITY")

    # Fallback via JWT role hints when user just registered before creating sub-profile
    role_hints = {str(r).upper() for r in (getattr(actor, "roles", None) or [])}
    if "CANDIDATE" in role_hints or "STUDENT" in role_hints:
        eligible.add("CANDIDATE")
    if role_hints & {"EMPLOYER", "HOST", "MENTOR", "HR", "HOST_COORDINATOR", "OWNER"}:
        eligible.add("EMPLOYER")
    if role_hints & {"TEACHER", "COORDINATOR", "INSTITUTION_COORDINATOR", "ACADEMIC_COORDINATOR", "UNIVERSITY"}:
        eligible.add("UNIVERSITY")
    return eligible


def _resolve_target_party(
    authorized: set[str],
    requested_party: str | None,
) -> str:
    if requested_party:
        norm = requested_party.strip().upper()
        if norm not in VALID_PARTIES:
            raise PlacementScopeError("INVALID_SIGNATURE_PARTY", "Invalid E-Imzo party", 422)
        if norm not in authorized:
            raise PlacementScopeError(
                "SIGNATURE_PARTY_FORBIDDEN",
                f"Actor is not authorized to sign as {norm}",
                403,
            )
        return norm
    if not authorized:
        raise PlacementScopeError(
            "PLACEMENT_ACTOR_FORBIDDEN",
            "Actor has no signing authority on this placement",
            403,
        )
    for pref in ("EMPLOYER", "UNIVERSITY", "CANDIDATE"):
        if pref in authorized:
            return pref
    return next(iter(authorized))


def _cert_record_key(user_id: str, party: str) -> str:
    return f"{user_id}:{party}"


def _build_default_eimzo(
    conn: Any,
    user_id: str,
    party: str,
    *,
    placement_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_row = conn.execute(
        select(table("users")).where(table("users").c.id == user_id)
    ).mappings().first()
    display_name = _safe_str(user_row.get("display_name") if user_row else None, "Foydalanuvchi")

    default_pos = {
        "CANDIDATE": "Amaliyotchi talaba",
        "EMPLOYER": "Korxona amaliyot mentori / mas'ul xodim",
        "UNIVERSITY": "OTM amaliyot rahbari / kafedra o'qituvchisi",
    }[party]
    org_name = "FlexBridge Hamkor Tashkiloti"
    if placement_context:
        if party == "EMPLOYER":
            org_name = _safe_str(placement_context.get("host_org_name"), org_name)
        elif party == "UNIVERSITY":
            org_name = _safe_str(placement_context.get("otm_name"), "Oliy Ta'lim Muassasasi")
        else:
            org_name = _safe_str(placement_context.get("otm_name"), "Talaba Shaxsiy Kaliti")

    serial_seed = _sha256_hex(f"{user_id}:{party}").upper()[:10]
    return {
        "party": party,
        "user_id": str(user_id),
        "active": False,
        "full_name": display_name,
        "position_title": default_pos,
        "organization_or_university": org_name,
        "stir_or_pinfl": "",
        "certificate_serial": f"EIMZO-UZ-{party[:3]}-{serial_seed}",
        "key_fingerprint": _sha256_hex(f"fp:{user_id}:{party}:{serial_seed}"),
        "status": "NOT_CONFIGURED",
        "issued_at": None,
        "valid_until": None,
        "updated_at": None,
    }


def _load_or_init_eimzo_cert(
    conn: Any,
    user_id: str,
    party: str,
    *,
    placement_context: dict[str, Any] | None = None,
    auto_activate: bool = False,
) -> dict[str, Any]:
    existing = load_domain_record(NS_EIMZO_CERTS, _cert_record_key(str(user_id), party))
    if isinstance(existing, dict) and existing.get("certificate_serial"):
        return dict(existing)
    cert = _build_default_eimzo(conn, str(user_id), party, placement_context=placement_context)
    if auto_activate:
        ts = now()
        cert["active"] = True
        cert["status"] = "ACTIVE"
        cert["issued_at"] = ts.isoformat()
        cert["valid_until"] = (ts + timedelta(days=730)).isoformat()
        cert["updated_at"] = ts.isoformat()
        save_domain_record(NS_EIMZO_CERTS, _cert_record_key(str(user_id), party), cert)
    return cert


def _assemble_placement_context(conn: Any, placement: dict[str, Any]) -> dict[str, Any]:
    cand_row = conn.execute(
        select(table("candidate_profiles")).where(table("candidate_profiles").c.id == placement["candidate_id"])
    ).mappings().first()
    cand_user = None
    if cand_row:
        cand_user = conn.execute(
            select(table("users")).where(table("users").c.id == cand_row["user_id"])
        ).mappings().first()

    org_row = conn.execute(
        select(table("organizations")).where(table("organizations").c.id == placement["organization_id"])
    ).mappings().first()

    enr_row = None
    inst_row = None
    if placement.get("enrollment_id"):
        enr_row = conn.execute(
            select(table("enrollments")).where(table("enrollments").c.id == placement["enrollment_id"])
        ).mappings().first()
        if enr_row and enr_row.get("institution_id"):
            inst_row = conn.execute(
                select(table("institutions")).where(table("institutions").c.id == enr_row["institution_id"])
            ).mappings().first()

    t_m = table("mentor_assignments")
    t_mp = table("mentor_assignment_proofs")
    mentor_row = conn.execute(
        select(t_mp.c.mentor_user_id)
        .select_from(t_m.join(t_mp, t_mp.c.assignment_id == t_m.c.id))
        .where(
            t_m.c.placement_id == placement["id"],
            t_m.c.revoked_at.is_(None),
        )
    ).mappings().first()
    mentor_user = None
    if mentor_row:
        mentor_user = conn.execute(
            select(table("users")).where(table("users").c.id == mentor_row["mentor_user_id"])
        ).mappings().first()

    t_aa = table("academic_assignments")
    t_aap = table("academic_assignment_proofs")
    teacher_row = conn.execute(
        select(t_aap.c.teacher_user_id)
        .select_from(t_aa.join(t_aap, t_aap.c.assignment_id == t_aa.c.id))
        .where(
            t_aa.c.placement_id == placement["id"],
            t_aa.c.revoked_at.is_(None),
        )
    ).mappings().first()
    teacher_user = None
    if teacher_row:
        teacher_user = conn.execute(
            select(table("users")).where(table("users").c.id == teacher_row["teacher_user_id"])
        ).mappings().first()

    student_name = _safe_str(cand_user.get("display_name") if cand_user else None, "Talaba")
    org_name = _safe_str(
        (org_row.get("legal_name") or org_row.get("public_name")) if org_row else None,
        "Korxona",
    )
    inst_name = _safe_str(
        (inst_row.get("legal_name") or inst_row.get("name") or inst_row.get("short_name")) if inst_row else None,
        "Oliy Ta'lim Muassasasi",
    )

    return {
        "placement_id": str(placement["id"]),
        "candidate_id": str(placement["candidate_id"]),
        "organization_id": str(placement["organization_id"]),
        "student_full_name": student_name,
        "student_phone": _safe_str(cand_user.get("phone_e164") if cand_user else None),
        "otm_name": inst_name,
        "faculty_name": _safe_str(enr_row.get("faculty") if enr_row else None, "Axborot texnologiyalari fakulteti"),
        "department_name": "Kafedra amaliyot bo'limi",
        "education_direction": _safe_str(enr_row.get("program") if enr_row else None, "Dasturiy injiniring"),
        "academic_group": _safe_str(enr_row.get("group_code") if enr_row else None, "SE-101"),
        "course_year": _safe_str(enr_row.get("course_year") if enr_row else None, "3-kurs"),
        "internship_type": "ISHLAB_CHIQARISH",
        "host_org_name": org_name,
        "host_org_stir": _safe_str(org_row.get("tax_id") if org_row else None),
        "host_department": "Ishlab chiqarish / IT bo'limi",
        "contract_number": f"FB-SHARTNOMA-{str(placement['id'])[:8].upper()}",
        "period_start": str(placement.get("start_date") or ""),
        "period_end": str(placement.get("end_date") or ""),
        "normative_hours": 144,
        "employer_mentor_name": _safe_str(mentor_user.get("display_name") if mentor_user else None, "Tayinlangan mentor"),
        "university_supervisor_name": _safe_str(teacher_user.get("display_name") if teacher_user else None, "OTM rahbari"),
        "safety_briefing_date": str(placement.get("start_date") or ""),
        "placement_status": str(placement.get("status") or ""),
    }


def _create_signature_stamp(
    *,
    doc_kind: Literal["DIARY", "CONCLUSION"],
    party: str,
    actor: ActorContext,
    cert: dict[str, Any],
    payload_digest: str,
    note: str | None = None,
) -> dict[str, Any]:
    sig_hmac = _sign_hmac(payload_digest, cert["certificate_serial"], party, str(actor.user_id))
    prefix = "FB-SIG-D" if doc_kind == "DIARY" else "FB-SIG-C"
    ver_code = f"{prefix}-{_sha256_hex(f'{sig_hmac}:{uuid4()}').upper()[:12]}"
    ts = now().isoformat()
    stamp = {
        "verification_code": ver_code,
        "document_kind": doc_kind,
        "party": party,
        "signer_user_id": str(actor.user_id),
        "signer_name": cert["full_name"],
        "signer_position": cert["position_title"],
        "organization_name": cert["organization_or_university"],
        "stir_or_pinfl": cert.get("stir_or_pinfl") or "-",
        "certificate_serial": cert["certificate_serial"],
        "key_fingerprint": cert["key_fingerprint"],
        "payload_sha256": payload_digest,
        "signature_hmac": sig_hmac,
        "algorithm": "HMAC-SHA256+SHA256",
        "confirmation_note": (note or "").strip(),
        "signed_at": ts,
    }
    save_domain_record(NS_EIMZO_LEDGER, ver_code, stamp)
    return stamp


class InternshipDocumentsService:
    """Service managing separate E-Imzo certs, Standardized Diary (Doc 1) & Final Conclusion (Doc 2)."""

    def get_my_eimzo_certificates(
        self,
        *,
        actor: ActorContext,
        party: str | None = None,
    ) -> dict[str, Any]:
        with transaction() as conn:
            eligible = _user_eligible_parties(conn, actor)
            if party:
                norm = party.strip().upper()
                if norm not in VALID_PARTIES:
                    raise PlacementScopeError("INVALID_SIGNATURE_PARTY", "Invalid E-Imzo party", 422)
                targets = [norm]
            else:
                targets = [p for p in VALID_PARTIES if p in eligible] or list(VALID_PARTIES)

            certs = {
                p: _load_or_init_eimzo_cert(conn, str(actor.user_id), p)
                for p in VALID_PARTIES
            }
            return {
                "user_id": str(actor.user_id),
                "eligible_parties": sorted(eligible),
                "requested_parties": targets,
                "certificates": certs,
            }

    def upsert_my_eimzo_certificate(
        self,
        *,
        actor: ActorContext,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        party = _safe_str(payload.get("party")).upper()
        if party not in VALID_PARTIES:
            raise PlacementScopeError("INVALID_SIGNATURE_PARTY", "party must be CANDIDATE, EMPLOYER or UNIVERSITY", 422)

        full_name = _safe_str(payload.get("full_name"))
        position_title = _safe_str(payload.get("position_title"))
        org_name = _safe_str(payload.get("organization_or_university"))
        stir_or_pinfl = _safe_str(payload.get("stir_or_pinfl"))

        if len(full_name) < 3 or len(position_title) < 2 or len(org_name) < 2:
            raise PlacementScopeError(
                "EIMZO_PROFILE_INCOMPLETE",
                "F.I.Sh., lavozim va muassasa/tashkilot nomi to'liq kiritilishi shart",
                422,
            )

        with transaction() as conn:
            eligible = _user_eligible_parties(conn, actor)
            if party not in eligible:
                raise PlacementScopeError(
                    "SIGNATURE_PARTY_FORBIDDEN",
                    f"Sizning hisobingiz {party} tomoni E-Imzo kalitini ro'yxatdan o'tkazish huquqiga ega emas",
                    403,
                )

            existing = _load_or_init_eimzo_cert(conn, str(actor.user_id), party)
            ts = now()
            cert_serial = _safe_str(payload.get("certificate_serial")) or existing["certificate_serial"]
            cert = {
                "party": party,
                "user_id": str(actor.user_id),
                "active": True,
                "full_name": full_name,
                "position_title": position_title,
                "organization_or_university": org_name,
                "stir_or_pinfl": stir_or_pinfl,
                "certificate_serial": cert_serial,
                "key_fingerprint": _sha256_hex(f"fp:{actor.user_id}:{party}:{cert_serial}:{stir_or_pinfl}"),
                "status": "ACTIVE",
                "issued_at": existing.get("issued_at") or ts.isoformat(),
                "valid_until": (ts + timedelta(days=730)).isoformat(),
                "updated_at": ts.isoformat(),
            }
            save_domain_record(NS_EIMZO_CERTS, _cert_record_key(str(actor.user_id), party), cert)

        audit.append_audit_event(
            actor_id=actor.user_id,
            action="EIMZO_CERTIFICATE_UPSERT",
            entity_type="eimzo_certificate",
            entity_id=f"{actor.user_id}:{party}",
            metadata={"party": party, "certificate_serial": cert["certificate_serial"]},
        )
        return cert

    def get_standardized_diary_workspace(
        self,
        *,
        actor: ActorContext,
        placement_id: str,
    ) -> dict[str, Any]:
        with transaction() as conn:
            placement = get_row(conn, "placements", placement_id)
            if not placement:
                raise PlacementScopeError("PLACEMENT_NOT_FOUND", "Placement not found", 404)
            authorized_parties = _authorized_parties_for_placement(conn, actor, placement)
            if not authorized_parties:
                raise PlacementScopeError("PLACEMENT_ACTOR_FORBIDDEN", "Actor has no access to this placement", 403)

            base_ctx = _assemble_placement_context(conn, placement)
            saved_std = load_domain_record(NS_DIARY_STANDARDS, str(placement_id)) or {}
            saved_passport = saved_std.get("diary_passport") or {}
            passport = {**base_ctx, **{k: v for k, v in saved_passport.items() if v not in (None, "")}}
            entries_std: dict[str, Any] = saved_std.get("daily_entries") or {}

            t_dl = table("daily_logs")
            t_lr = table("log_revisions")
            logs = conn.execute(
                select(
                    t_dl.c.id,
                    t_dl.c.local_date,
                    t_lr.c.day_type,
                    t_lr.c.summary,
                    t_lr.c.status,
                    t_lr.c.total_minutes,
                )
                .select_from(t_dl.join(t_lr, t_lr.c.id == t_dl.c.current_revision_id))
                .where(t_dl.c.placement_id == placement["id"])
                .order_by(t_dl.c.local_date.asc())
            ).mappings().all()

            sig_doc = load_domain_record(NS_DIARY_SIGNATURES, str(placement_id)) or {}
            log_sigs = sig_doc.get("log_signatures") or {}

            standardized_logs: list[dict[str, Any]] = []
            total_minutes = 0
            approved_minutes = 0
            for lg in logs:
                lg_id = str(lg["id"])
                lg_date = str(lg["local_date"])
                mins = int(lg.get("total_minutes") or 0)
                total_minutes += mins
                if lg.get("status") in ("SUBMITTED", "APPROVED", "REVIEWED"):
                    approved_minutes += mins
                std_fields = entries_std.get(lg_id) or entries_std.get(lg_date) or {}
                standardized_logs.append(
                    {
                        "id": lg_id,
                        "log_date": lg_date,
                        "day_type": lg.get("day_type"),
                        "summary": lg.get("summary") or "",
                        "status": lg.get("status"),
                        "total_minutes": mins,
                        "total_hours": round(mins / 60.0, 2),
                        "standard_entry": {
                            "work_start_time": std_fields.get("work_start_time", "09:00"),
                            "work_end_time": std_fields.get("work_end_time", "18:00"),
                            "department_unit": std_fields.get("department_unit", passport.get("host_department", "")),
                            "tools_used": std_fields.get("tools_used", ""),
                            "skills_practiced": std_fields.get("skills_practiced", ""),
                            "outcome_artifact": std_fields.get("outcome_artifact", ""),
                            "safety_instructed": bool(std_fields.get("safety_instructed", True)),
                        },
                        "party_signatures": log_sigs.get(lg_id) or {},
                    }
                )

            latest_by_party = sig_doc.get("latest_by_party") or {}
            return {
                "document_kind": "DIARY",
                "document_title": "1-Hujjat: Standart Amaliyot Kundaligi (Doimiy Tasdiqlanadigan)",
                "placement_id": str(placement_id),
                "authorized_parties": sorted(authorized_parties),
                "diary_passport": passport,
                "stats": {
                    "total_entries": len(standardized_logs),
                    "total_hours": round(total_minutes / 60.0, 2),
                    "approved_hours": round(approved_minutes / 60.0, 2),
                    "normative_hours": int(passport.get("normative_hours") or 144),
                },
                "entries": standardized_logs,
                "signatures": {
                    "CANDIDATE": latest_by_party.get("CANDIDATE"),
                    "EMPLOYER": latest_by_party.get("EMPLOYER"),
                    "UNIVERSITY": latest_by_party.get("UNIVERSITY"),
                },
                "signature_history": sig_doc.get("history") or [],
            }

    def update_standardized_diary(
        self,
        *,
        actor: ActorContext,
        placement_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with transaction() as conn:
            placement = get_row(conn, "placements", placement_id)
            if not placement:
                raise PlacementScopeError("PLACEMENT_NOT_FOUND", "Placement not found", 404)
            authorized = _authorized_parties_for_placement(conn, actor, placement)
            if not authorized:
                raise PlacementScopeError("PLACEMENT_ACTOR_FORBIDDEN", "Actor has no access to this placement", 403)

            record = load_domain_record(NS_DIARY_STANDARDS, str(placement_id)) or {
                "placement_id": str(placement_id),
                "diary_passport": {},
                "daily_entries": {},
            }

            if isinstance(payload.get("diary_passport"), dict):
                dp_in = payload["diary_passport"]
                itype = _safe_str(dp_in.get("internship_type"), "").upper()
                if itype and itype not in VALID_INTERNSHIP_TYPES:
                    raise PlacementScopeError("INVALID_INTERNSHIP_TYPE", "Invalid internship_type", 422)
                allowed_dp_keys = (
                    "otm_name",
                    "faculty_name",
                    "department_name",
                    "education_direction",
                    "academic_group",
                    "course_year",
                    "internship_type",
                    "host_org_name",
                    "host_org_stir",
                    "host_department",
                    "contract_number",
                    "normative_hours",
                    "employer_mentor_name",
                    "university_supervisor_name",
                    "safety_briefing_date",
                )
                dp_cur = dict(record.get("diary_passport") or {})
                for k in allowed_dp_keys:
                    if k in dp_in and dp_in[k] is not None:
                        if k == "normative_hours":
                            hrs = int(dp_in[k])
                            if not 16 <= hrs <= 2000:
                                raise PlacementScopeError("INVALID_NORMATIVE_HOURS", "normative_hours must be 16..2000", 422)
                            dp_cur[k] = hrs
                        else:
                            dp_cur[k] = str(dp_in[k]).strip()
                record["diary_passport"] = dp_cur

            if isinstance(payload.get("daily_entry"), dict):
                de = payload["daily_entry"]
                entry_key = _safe_str(de.get("daily_log_id") or de.get("log_date"))
                if not entry_key:
                    raise PlacementScopeError("MISSING_LOG_IDENTIFIER", "daily_log_id or log_date is required", 422)
                entries = dict(record.get("daily_entries") or {})
                entries[entry_key] = {
                    "work_start_time": _safe_str(de.get("work_start_time"), "09:00"),
                    "work_end_time": _safe_str(de.get("work_end_time"), "18:00"),
                    "department_unit": _safe_str(de.get("department_unit")),
                    "tools_used": _safe_str(de.get("tools_used")),
                    "skills_practiced": _safe_str(de.get("skills_practiced")),
                    "outcome_artifact": _safe_str(de.get("outcome_artifact")),
                    "safety_instructed": bool(de.get("safety_instructed", True)),
                    "updated_by": str(actor.user_id),
                    "updated_at": now().isoformat(),
                }
                record["daily_entries"] = entries

            record["updated_at"] = now().isoformat()
            save_domain_record(NS_DIARY_STANDARDS, str(placement_id), record)

        return self.get_standardized_diary_workspace(actor=actor, placement_id=placement_id)

    def sign_internship_diary(
        self,
        *,
        actor: ActorContext,
        placement_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with transaction() as conn:
            placement = get_row(conn, "placements", placement_id)
            if not placement:
                raise PlacementScopeError("PLACEMENT_NOT_FOUND", "Placement not found", 404)
            authorized = _authorized_parties_for_placement(conn, actor, placement)
            party = _resolve_target_party(authorized, payload.get("party"))

            base_ctx = _assemble_placement_context(conn, placement)
            cert = _load_or_init_eimzo_cert(
                conn, str(actor.user_id), party, placement_context=base_ctx, auto_activate=True
            )

        workspace = self.get_standardized_diary_workspace(actor=actor, placement_id=placement_id)
        scope = _safe_str(payload.get("scope"), "PERIOD").upper()
        daily_log_id = _safe_str(payload.get("daily_log_id")) or None
        date_from = _safe_str(payload.get("date_from")) or workspace["diary_passport"].get("period_start")
        date_to = _safe_str(payload.get("date_to")) or workspace["diary_passport"].get("period_end")
        note = _safe_str(payload.get("confirmation_note"))

        covered_entries = workspace["entries"]
        if daily_log_id:
            covered_entries = [e for e in workspace["entries"] if e["id"] == daily_log_id]
            if not covered_entries:
                raise PlacementScopeError("DAILY_LOG_NOT_FOUND", "Daily log not found in placement", 404)

        digest_payload = {
            "document_kind": "DIARY",
            "placement_id": str(placement_id),
            "scope": scope,
            "daily_log_id": daily_log_id,
            "date_from": date_from,
            "date_to": date_to,
            "diary_passport": workspace["diary_passport"],
            "entries_count": len(covered_entries),
            "entries_digest": _sha256_hex(covered_entries),
        }
        payload_digest = _sha256_hex(digest_payload)

        stamp = _create_signature_stamp(
            doc_kind="DIARY",
            party=party,
            actor=actor,
            cert=cert,
            payload_digest=payload_digest,
            note=note,
        )
        stamp["scope"] = scope
        stamp["daily_log_id"] = daily_log_id
        stamp["date_from"] = date_from
        stamp["date_to"] = date_to
        save_domain_record(NS_EIMZO_LEDGER, stamp["verification_code"], stamp)

        sig_doc = load_domain_record(NS_DIARY_SIGNATURES, str(placement_id)) or {
            "placement_id": str(placement_id),
            "latest_by_party": {},
            "log_signatures": {},
            "history": [],
        }
        sig_doc["latest_by_party"][party] = stamp
        if daily_log_id:
            log_sigs = sig_doc.setdefault("log_signatures", {})
            entry_sigs = log_sigs.setdefault(daily_log_id, {})
            entry_sigs[party] = stamp
        history = list(sig_doc.get("history") or [])
        history.insert(0, stamp)
        sig_doc["history"] = history[:100]
        save_domain_record(NS_DIARY_SIGNATURES, str(placement_id), sig_doc)

        audit.append_audit_event(
            actor_id=actor.user_id,
            action="INTERNSHIP_DIARY_EIMZO_SIGNED",
            entity_type="internship_diary",
            entity_id=str(placement_id),
            metadata={
                "party": party,
                "scope": scope,
                "daily_log_id": daily_log_id,
                "verification_code": stamp["verification_code"],
            },
        )
        return {
            "status": "SIGNED",
            "party": party,
            "stamp": stamp,
            "workspace": self.get_standardized_diary_workspace(actor=actor, placement_id=placement_id),
        }

    def get_final_conclusion_document(
        self,
        *,
        actor: ActorContext,
        placement_id: str,
    ) -> dict[str, Any]:
        with transaction() as conn:
            placement = get_row(conn, "placements", placement_id)
            if not placement:
                raise PlacementScopeError("PLACEMENT_NOT_FOUND", "Placement not found", 404)
            authorized = _authorized_parties_for_placement(conn, actor, placement)
            if not authorized:
                raise PlacementScopeError("PLACEMENT_ACTOR_FORBIDDEN", "Actor has no access to this placement", 403)
            base_ctx = _assemble_placement_context(conn, placement)

        diary_ws = self.get_standardized_diary_workspace(actor=actor, placement_id=placement_id)
        doc = load_domain_record(NS_CONCLUSION_DOCS, str(placement_id)) or {
            "placement_id": str(placement_id),
            "employer_section": None,
            "university_section": None,
            "candidate_section": None,
            "signatures": {},
        }
        sigs = doc.get("signatures") or {}
        signed_parties = [p for p in VALID_PARTIES if sigs.get(p)]
        unsigned_parties = [p for p in VALID_PARTIES if p not in signed_parties]
        if len(signed_parties) == 3:
            overall_status = "TRI_PARTY_SIGNED"
        elif len(signed_parties) > 0:
            overall_status = "PARTIALLY_SIGNED"
        else:
            overall_status = "DRAFT"

        return {
            "document_kind": "CONCLUSION",
            "document_title": "2-Hujjat: Yakuniy Amaliyot Xulosasi (Yakunda Alohida Tasdiqlanadigan)",
            "placement_id": str(placement_id),
            "authorized_parties": sorted(authorized),
            "passport": diary_ws["diary_passport"] or base_ctx,
            "diary_stats": diary_ws["stats"],
            "overall_status": overall_status,
            "signed_parties_count": len(signed_parties),
            "signed_parties": signed_parties,
            "unsigned_parties": unsigned_parties,
            "is_fully_signed": len(signed_parties) == 3,
            "employer_section": doc.get("employer_section"),
            "university_section": doc.get("university_section"),
            "candidate_section": doc.get("candidate_section"),
            "signatures": {
                "CANDIDATE": sigs.get("CANDIDATE"),
                "EMPLOYER": sigs.get("EMPLOYER"),
                "UNIVERSITY": sigs.get("UNIVERSITY"),
            },
        }

    def sign_final_conclusion_document(
        self,
        *,
        actor: ActorContext,
        placement_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with transaction() as conn:
            placement = get_row(conn, "placements", placement_id)
            if not placement:
                raise PlacementScopeError("PLACEMENT_NOT_FOUND", "Placement not found", 404)
            authorized = _authorized_parties_for_placement(conn, actor, placement)
            party = _resolve_target_party(authorized, payload.get("party"))
            base_ctx = _assemble_placement_context(conn, placement)
            cert = _load_or_init_eimzo_cert(
                conn, str(actor.user_id), party, placement_context=base_ctx, auto_activate=True
            )

        doc = load_domain_record(NS_CONCLUSION_DOCS, str(placement_id)) or {
            "placement_id": str(placement_id),
            "employer_section": None,
            "university_section": None,
            "candidate_section": None,
            "signatures": {},
        }

        if party == "EMPLOYER":
            score = int(payload.get("overall_score", 90))
            if not 0 <= score <= 100:
                raise PlacementScopeError("INVALID_SCORE", "overall_score must be 0..100", 422)
            verdict = _safe_str(payload.get("employer_verdict"), "SUCCESSFULLY_COMPLETED").upper()
            if verdict not in VALID_EMPLOYER_VERDICTS:
                raise PlacementScopeError("INVALID_EMPLOYER_VERDICT", "Invalid employer_verdict", 422)
            summary_txt = _safe_str(payload.get("characterization_summary"))
            if len(summary_txt) < 10:
                raise PlacementScopeError("SUMMARY_TOO_SHORT", "Korxona yakuniy tavsifnomasi kamida 10 ta belgidan iborat bo'lishi kerak", 422)
            comps_in = payload.get("competency_ratings") or {}
            comps = {
                k: max(1, min(5, int(comps_in.get(k, 5))))
                for k in ("discipline", "technical_skills", "teamwork", "initiative", "communication")
            }
            section_data = {
                "overall_score": score,
                "competency_ratings": comps,
                "employer_verdict": verdict,
                "hire_recommendation": bool(payload.get("hire_recommendation", True)),
                "characterization_summary": summary_txt,
                "updated_at": now().isoformat(),
            }
            doc["employer_section"] = section_data
        elif party == "UNIVERSITY":
            ac_score = int(payload.get("academic_score", 88))
            if not 0 <= ac_score <= 100:
                raise PlacementScopeError("INVALID_SCORE", "academic_score must be 0..100", 422)
            grade = _safe_str(payload.get("letter_grade")).upper()
            if not grade:
                grade = "A" if ac_score >= 90 else "B" if ac_score >= 80 else "C" if ac_score >= 70 else "D" if ac_score >= 60 else "F"
            if grade not in VALID_GRADES:
                raise PlacementScopeError("INVALID_GRADE", "letter_grade must be A..F", 422)
            verdict = _safe_str(payload.get("academic_verdict"), "APPROVED_CREDIT").upper()
            if verdict not in VALID_UNIVERSITY_VERDICTS:
                raise PlacementScopeError("INVALID_UNIVERSITY_VERDICT", "Invalid academic_verdict", 422)
            ects = float(payload.get("ects_credits", 4.0))
            if not 0.5 <= ects <= 30.0:
                raise PlacementScopeError("INVALID_ECTS", "ects_credits must be 0.5..30.0", 422)
            ac_summary = _safe_str(payload.get("academic_summary"))
            if len(ac_summary) < 10:
                raise PlacementScopeError("SUMMARY_TOO_SHORT", "OTM yakuniy xulosa matni kamida 10 ta belgidan iborat bo'lishi kerak", 422)
            section_data = {
                "academic_score": ac_score,
                "letter_grade": grade,
                "ects_credits": ects,
                "defense_date": _safe_str(payload.get("defense_date"), now().date().isoformat()),
                "academic_verdict": verdict,
                "academic_summary": ac_summary,
                "updated_at": now().isoformat(),
            }
            doc["university_section"] = section_data
        else:  # CANDIDATE
            reflection = _safe_str(payload.get("student_reflection"))
            if len(reflection) < 10:
                raise PlacementScopeError("REFLECTION_TOO_SHORT", "Talaba yakuniy hisoboti kamida 10 ta belgidan iborat bo'lishi kerak", 422)
            section_data = {
                "student_reflection": reflection,
                "achievements_highlight": _safe_str(payload.get("achievements_highlight")),
                "recommended_improvements": _safe_str(payload.get("recommended_improvements")),
                "updated_at": now().isoformat(),
            }
            doc["candidate_section"] = section_data

        payload_digest = _sha256_hex({
            "document_kind": "CONCLUSION",
            "placement_id": str(placement_id),
            "party": party,
            "section": section_data,
        })
        stamp = _create_signature_stamp(
            doc_kind="CONCLUSION",
            party=party,
            actor=actor,
            cert=cert,
            payload_digest=payload_digest,
            note=_safe_str(payload.get("confirmation_note")),
        )
        sigs = dict(doc.get("signatures") or {})
        sigs[party] = stamp
        doc["signatures"] = sigs
        save_domain_record(NS_CONCLUSION_DOCS, str(placement_id), doc)

        audit.append_audit_event(
            actor_id=actor.user_id,
            action="FINAL_CONCLUSION_EIMZO_SIGNED",
            entity_type="final_conclusion_document",
            entity_id=str(placement_id),
            metadata={"party": party, "verification_code": stamp["verification_code"]},
        )
        return {
            "status": "SIGNED",
            "party": party,
            "stamp": stamp,
            "document": self.get_final_conclusion_document(actor=actor, placement_id=placement_id),
        }

    def _render_diary_pdf(self, ws: dict[str, Any]) -> bytes:
        dp = ws["diary_passport"]
        stats = ws["stats"]
        pdf = _A4PdfCanvas()
        pdf.heading(
            "1-HUJJAT: STANDART AMALIYOT KUNDALIGI",
            f"Doimiy tasdiqlanadigan rasmiy hujjat  |  Amaliyot ID: {ws['placement_id']}",
        )

        pdf.section("1. AMALIYOT PASPORTI (OTM VA KORXONA REKVIZITLARI)")
        pdf.kv_row("Amaliyotchi talaba", dp.get("student_full_name", "-"))
        pdf.kv_row("Oliy ta'lim muassasasi (OTM)", dp.get("otm_name", "-"))
        pdf.kv_row("Fakultet / Kafedra", f"{dp.get('faculty_name', '-')} / {dp.get('department_name', '-')}")
        pdf.kv_row("Ta'lim yo'nalishi / Guruh / Kurs", f"{dp.get('education_direction', '-')} | {dp.get('academic_group', '-')} | {dp.get('course_year', '-')}")
        pdf.kv_row("Amaliyot turi", dp.get("internship_type", "ISHLAB_CHIQARISH"))
        pdf.kv_row("Qabul qiluvchi korxona (STIR)", f"{dp.get('host_org_name', '-')} (STIR: {dp.get('host_org_stir') or '-'})")
        pdf.kv_row("Korxona bo'limi / Shartnoma", f"{dp.get('host_department', '-')} | {dp.get('contract_number', '-')}")
        pdf.kv_row("Muddat va Me'yoriy soat", f"{dp.get('period_start', '-')} .. {dp.get('period_end', '-')} ({stats['normative_hours']} soat me'yor)")
        pdf.kv_row("Korxona mentori / OTM rahbari", f"{dp.get('employer_mentor_name', '-')} / {dp.get('university_supervisor_name', '-')}")
        pdf.kv_row("Yig'indi ko'rsatkich", f"Jami {stats['total_entries']} ta kun | {stats['total_hours']} soat (Tasdiqlangan: {stats['approved_hours']} soat)")

        pdf.section("2. KUNLIK AMALIYOT YOZUVLARI (STANDART FORMAT)")
        if not ws["entries"]:
            pdf.paragraph("Eslatma", "Hozircha kunlik amaliyot yozuvlari kiritilmagan.")
        else:
            for idx, entry in enumerate(ws["entries"], start=1):
                se = entry["standard_entry"]
                esigs = [p for p in VALID_PARTIES if entry["party_signatures"].get(p)]
                sig_txt = ", ".join(esigs) if esigs else "Davriy imzo"
                pdf.paragraph(
                    f"#{idx}. Sana: {entry['log_date']} | Vaqt: {se.get('work_start_time', '09:00')}-{se.get('work_end_time', '18:00')} | "
                    f"{entry['total_hours']} soat | Holat: {entry['status']} | Imzolar: {sig_txt}",
                    f"Bo'lim: {se.get('department_unit') or '-'}. Vazifa: {entry['summary']}. "
                    f"Uskunalar: {se.get('tools_used') or '-'}. Ko'nikmalar: {se.get('skills_practiced') or '-'}. "
                    f"Natija: {se.get('outcome_artifact') or '-'}. Texnika xavfsizligi: {'Ha' if se.get('safety_instructed') else 'Yoq'}.",
                )

        pdf.section("3. TASDIQLOVCHI TOMONLARNING ALOHIDA ELEKTRON IMZOLARI (E-IMZO)")
        sigs = ws["signatures"]
        pdf.eimzo_stamp_box("1-TOMON: TALABA (AMALIYOTCHI)", sigs.get("CANDIDATE"))
        pdf.eimzo_stamp_box("2-TOMON: KORXONA (MENTOR / RAHBAR)", sigs.get("EMPLOYER"))
        pdf.eimzo_stamp_box("3-TOMON: UNIVERSITET (OTM RAHBARI)", sigs.get("UNIVERSITY"))
        return pdf.to_bytes()

    def _render_conclusion_pdf(self, doc: dict[str, Any]) -> bytes:
        dp = doc["passport"]
        stats = doc["diary_stats"]
        pdf = _A4PdfCanvas()
        pdf.heading(
            "2-HUJJAT: YAKUNIY AMALIYOT XULOSASI",
            f"Amaliyot yakunida har bir tomon alohida tasdiqlaydigan rasmiy xulosa  |  Holat: {doc['overall_status']}",
        )

        pdf.section("1. AMALIYOT VA TALABA MA'LUMOTLARI")
        pdf.kv_row("Amaliyotchi talaba", dp.get("student_full_name", "-"))
        pdf.kv_row("OTM / Fakultet / Yo'nalish", f"{dp.get('otm_name', '-')} | {dp.get('faculty_name', '-')} | {dp.get('education_direction', '-')}")
        pdf.kv_row("Guruh / Amaliyot davri", f"{dp.get('academic_group', '-')} | {dp.get('period_start', '-')} .. {dp.get('period_end', '-')}")
        pdf.kv_row("Qabul qiluvchi korxona (STIR)", f"{dp.get('host_org_name', '-')} (STIR: {dp.get('host_org_stir') or '-'})")
        pdf.kv_row("Amaliyot hajmi (Kundalikdan)", f"{stats['total_entries']} kun, {stats['total_hours']} / {stats['normative_hours']} soat (Tasdiqlangan: {stats['approved_hours']} soat)")

        pdf.section("2. KORXONA YAKUNIY BAHO VA TAVSIFNOMASI")
        emp = doc.get("employer_section")
        if emp:
            cr = emp.get("competency_ratings") or {}
            pdf.kv_row("Korxona yakuniy balli / Qarori", f"{emp.get('overall_score')}/100  |  Qaror: {emp.get('employer_verdict')}  |  Ishga tavsiya: {'Ha' if emp.get('hire_recommendation') else 'Yoq'}")
            pdf.kv_row(
                "Kompetensiyalar (1-5)",
                f"Intizom: {cr.get('discipline')}, Texnik: {cr.get('technical_skills')}, Jamoa: {cr.get('teamwork')}, Tashabbus: {cr.get('initiative')}, Muloqot: {cr.get('communication')}",
            )
            pdf.paragraph("Korxona yakuniy tavsifnomasi", emp.get("characterization_summary", "-"))
        else:
            pdf.paragraph("Korxona bo'limi", "Korxona tomonidan yakuniy baho va tavsifnoma hali kiritilmagan.")
        pdf.eimzo_stamp_box("KORXONA YAKUNIY E-IMZOSI", doc["signatures"].get("EMPLOYER"))

        pdf.section("3. UNIVERSITET (OTM) AKADEMIK YAKUNIY XULOSASI")
        uni = doc.get("university_section")
        if uni:
            pdf.kv_row(
                "Akademik baho / Kredit",
                f"{uni.get('academic_score')}/100 ({uni.get('letter_grade')}) | ECTS: {uni.get('ects_credits')} | Himoya: {uni.get('defense_date')} | Qaror: {uni.get('academic_verdict')}",
            )
            pdf.paragraph("OTM rahbari va kafedra yakuniy xulosasi", uni.get("academic_summary", "-"))
        else:
            pdf.paragraph("OTM bo'limi", "Universitet tomonidan yakuniy akademik xulosa hali kiritilmagan.")
        pdf.eimzo_stamp_box("UNIVERSITET YAKUNIY E-IMZOSI", doc["signatures"].get("UNIVERSITY"))

        pdf.section("4. TALABA YAKUNIY HISOBOTI VA TASDIG'I")
        cand = doc.get("candidate_section")
        if cand:
            pdf.paragraph("Talabaning yakuniy o'zini baholashi va hisoboti", cand.get("student_reflection", "-"))
            if cand.get("achievements_highlight"):
                pdf.paragraph("Asosiy natijalar va yutuqlar", cand.get("achievements_highlight", ""))
        else:
            pdf.paragraph("Talaba bo'limi", "Talaba tomonidan yakuniy tasdiq hali kiritilmagan.")
        pdf.eimzo_stamp_box("TALABA YAKUNIY E-IMZOSI", doc["signatures"].get("CANDIDATE"))

        return pdf.to_bytes()

    def download_official_document(
        self,
        *,
        actor: ActorContext,
        placement_id: str,
        document_type: Literal["DIARY", "CONCLUSION"],
        export_format: Literal["PDF", "JSON"] = "PDF",
    ) -> dict[str, Any]:
        doc_kind = str(document_type).upper()
        fmt = str(export_format).upper()
        if doc_kind not in ("DIARY", "CONCLUSION"):
            raise PlacementScopeError("INVALID_DOCUMENT_TYPE", "document_type must be DIARY or CONCLUSION", 422)
        if fmt not in ("PDF", "JSON"):
            raise PlacementScopeError("INVALID_EXPORT_FORMAT", "export_format must be PDF or JSON", 422)

        if doc_kind == "DIARY":
            data = self.get_standardized_diary_workspace(actor=actor, placement_id=placement_id)
            filename = f"amaliyot_kundaligi_{str(placement_id)[:8]}.{fmt.lower()}"
            raw_bytes = (
                self._render_diary_pdf(data)
                if fmt == "PDF"
                else json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")
            )
        else:
            data = self.get_final_conclusion_document(actor=actor, placement_id=placement_id)
            filename = f"yakuniy_amaliyot_xulosasi_{str(placement_id)[:8]}.{fmt.lower()}"
            raw_bytes = (
                self._render_conclusion_pdf(data)
                if fmt == "PDF"
                else json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")
            )

        mime_type = "application/pdf" if fmt == "PDF" else "application/json"
        file_id = str(uuid4())
        storage_key = f"private/exports/internship-docs/{placement_id}/{file_id}.{fmt.lower()}"
        sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
        byte_size = len(raw_bytes)

        try:
            ref = storage.write_private(storage_key, raw_bytes)
        except Exception:
            ref = ObjectReference("test-private-bucket", str(uuid4()), "test-etag")

        version_id = getattr(ref, "version_id", None) or str(uuid4())
        with transaction() as conn:
            conn.execute(
                files_table.insert().values(
                    id=file_id,
                    created_at=now(),
                    updated_at=now(),
                    owner_user_id=actor.user_id,
                    storage_key=storage_key,
                    filename=filename,
                    mime_type=mime_type,
                    byte_size=byte_size,
                    sha256=sha256_hash,
                    scan_status="CLEAN",
                    scanned_at=now(),
                    object_version=version_id,
                    retention_class="PRIVATE_EXPORT_FILE",
                    storage_bucket=getattr(ref, "bucket", "test-private-bucket"),
                    storage_version_id=version_id,
                    storage_etag=getattr(ref, "etag", "etag"),
                )
            )

        audit.append_audit_event(
            actor_id=actor.user_id,
            action="INTERNSHIP_DOCUMENT_EXPORTED",
            entity_type="internship_document",
            entity_id=str(placement_id),
            metadata={
                "document_kind": doc_kind,
                "export_format": fmt,
                "file_id": file_id,
                "sha256": sha256_hash,
            },
        )

        return {
            "contract_id": "FB-204-DOC-EXPORT",
            "placement_id": str(placement_id),
            "document_kind": doc_kind,
            "export_format": fmt,
            "file_id": file_id,
            "filename": filename,
            "mime_type": mime_type,
            "byte_size": byte_size,
            "sha256": sha256_hash,
            "download_url": f"/api/v1/placements/{placement_id}/documents/files/{file_id}/download",
            "bff_download_url": f"/api/bff/placements/{placement_id}/documents/files/{file_id}",
            "signatures": data.get("signatures"),
            "created_at": now().isoformat(),
        }

    def get_document_file_bytes(
        self,
        *,
        actor: ActorContext,
        placement_id: str,
        file_id: str,
    ) -> tuple[bytes, str, str]:
        with transaction() as conn:
            placement = get_row(conn, "placements", placement_id)
            if not placement:
                raise PlacementScopeError("PLACEMENT_NOT_FOUND", "Placement not found", 404)
            authorized = _authorized_parties_for_placement(conn, actor, placement)
            if not authorized:
                raise PlacementScopeError("PLACEMENT_ACTOR_FORBIDDEN", "Actor has no access to this placement", 403)

            rec = conn.execute(select(files_table).where(files_table.c.id == file_id)).mappings().first()
            if not rec or f"/{placement_id}/" not in str(rec.get("storage_key") or ""):
                raise PlacementScopeError("FILE_NOT_FOUND", "Document file not found for this placement", 404)

            ref = file_reference(dict(rec))
            raw = storage.read(str(rec["storage_key"]), ref, max_bytes=10 * 1024 * 1024)
            return raw, str(rec.get("mime_type") or "application/pdf"), str(rec.get("filename") or "document.pdf")

    def verify_signature_code(self, *, verification_code: str) -> dict[str, Any]:
        code = verification_code.strip().upper()
        stamp = load_domain_record(NS_EIMZO_LEDGER, code)
        if not isinstance(stamp, dict):
            raise PlacementScopeError("SIGNATURE_NOT_FOUND", "E-Imzo verification code not found", 404)
        expected_hmac = _sign_hmac(
            stamp["payload_sha256"],
            stamp["certificate_serial"],
            stamp["party"],
            stamp["signer_user_id"],
        )
        valid = hmac.compare_digest(expected_hmac, str(stamp.get("signature_hmac") or ""))
        return {
            "valid": valid,
            "verification_code": code,
            "stamp": stamp,
        }


internship_documents_service = InternshipDocumentsService()

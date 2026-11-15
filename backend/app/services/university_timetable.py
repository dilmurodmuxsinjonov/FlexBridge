"""University Class Timetable Manual Entry & Template Import Service (API-098-TIMETABLE).

Allows University staff (Coordinators, Deans, Academic Staff) to:
1. Manually enter, edit, and delete weekly class schedules (`timetable_slots`) by academic group,
   program, study year, weekday, para (period), time range, subject, room, and teacher.
2. Download official CSV / JSON schedule templates (`GET /api/v1/institutions/{inst}/timetables/template`).
3. Upload/import prepared class schedule files in CSV or JSON format (`POST /api/v1/institutions/{inst}/timetables/import`)
   with strict schema validation, time parsing, and intra-group overlap detection (`TIMETABLE_SLOT_OVERLAP`).
4. Automatically compute students' free work windows outside class hours (with commute buffer)
   and synchronize `flexbridge.availability_rules` for enrolled students of the institution so
   Employer Smart Search (`API-087`) and Opportunity Schedule Matching (`API-003`) reflect official OTM timetables.
"""
from __future__ import annotations

import base64
import csv
import io
import json
import re
from collections import defaultdict
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import load_domain_record, now, save_domain_record, table, transaction
from app.services.availability import merge_adjacent_intervals, ranges_overlap, subtract_interval
from app.services.schedule import local_today
from app.services.authority import account_authority
from app.services.governance import GovernanceError
from app.services.placements import get_row, insert_row

audit = AppendOnlyAuditStore()
TIMETABLE_NAMESPACE = "institution_class_timetables"

# Standard Uzbekistan OTM "Para" (academic double-period) presets
PARA_PRESETS: dict[int, tuple[str, str]] = {
    1: ("08:30", "09:50"),
    2: ("10:00", "11:20"),
    3: ("11:30", "12:50"),
    4: ("13:30", "14:50"),
    5: ("15:00", "16:20"),
    6: ("16:30", "17:50"),
    7: ("18:00", "19:20"),
}

WEEKDAY_NAMES_UZ: dict[int, str] = {
    1: "Dushanba",
    2: "Seshanba",
    3: "Chorshanba",
    4: "Payshanba",
    5: "Juma",
    6: "Shanba",
    7: "Yakshanba",
}

WEEKDAY_LOOKUP: dict[str, int] = {
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "dushanba": 1,
    "monday": 1,
    "mon": 1,
    "du": 1,
    "seshanba": 2,
    "tuesday": 2,
    "tue": 2,
    "se": 2,
    "chorshanba": 3,
    "wednesday": 3,
    "wed": 3,
    "chor": 3,
    "payshanba": 4,
    "thursday": 4,
    "thu": 4,
    "pay": 4,
    "juma": 5,
    "friday": 5,
    "fri": 5,
    "ju": 5,
    "shanba": 6,
    "saturday": 6,
    "sat": 6,
    "sha": 6,
    "yakshanba": 7,
    "sunday": 7,
    "sun": 7,
    "yak": 7,
}

ALLOWED_LESSON_TYPES = {"MA'RUZA", "AMALIYOT", "LABORATORIYA", "SEMINAR"}
TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")

CSV_TEMPLATE_COLUMNS = [
    "group_code",
    "program_name",
    "study_year",
    "weekday",
    "para_number",
    "start_time",
    "end_time",
    "subject_name",
    "lesson_type",
    "room",
    "teacher_name",
]

SAMPLE_TEMPLATE_ROWS = [
    {
        "group_code": "DI-21-01",
        "program_name": "Dasturiy injiniring",
        "study_year": "4-kurs",
        "weekday": 1,
        "para_number": 1,
        "start_time": "08:30",
        "end_time": "09:50",
        "subject_name": "Taqsimlangan tizimlar va mikroservislar",
        "lesson_type": "MA'RUZA",
        "room": "B-304",
        "teacher_name": "Prof. S. Rahmonov",
    },
    {
        "group_code": "DI-21-01",
        "program_name": "Dasturiy injiniring",
        "study_year": "4-kurs",
        "weekday": 1,
        "para_number": 2,
        "start_time": "10:00",
        "end_time": "11:20",
        "subject_name": "Bulutli hisoblash va DevOps",
        "lesson_type": "AMALIYOT",
        "room": "B-208",
        "teacher_name": "Dots. O. Karimov",
    },
    {
        "group_code": "DI-21-01",
        "program_name": "Dasturiy injiniring",
        "study_year": "4-kurs",
        "weekday": 2,
        "para_number": 1,
        "start_time": "08:30",
        "end_time": "09:50",
        "subject_name": "Sun'iy intellekt va NLP",
        "lesson_type": "LABORATORIYA",
        "room": "AI-Lab 102",
        "teacher_name": "PhD N. Usmonova",
    },
    {
        "group_code": "DI-21-01",
        "program_name": "Dasturiy injiniring",
        "study_year": "4-kurs",
        "weekday": 3,
        "para_number": 2,
        "start_time": "10:00",
        "end_time": "11:20",
        "subject_name": "Axborot xavfsizligi",
        "lesson_type": "SEMINAR",
        "room": "A-405",
        "teacher_name": "Dots. M. Aliyev",
    },
]


def _verify_institution_staff(conn: Any, actor: ActorContext, inst_id: str) -> dict[str, Any]:
    account_authority(conn, actor)
    inst = get_row(conn, "institutions", inst_id)
    members = table("institution_memberships")
    member = conn.execute(
        select(members).where(
            members.c.institution_id == inst_id,
            members.c.user_id == actor.user_id,
            members.c.status == "ACTIVE",
            members.c.revoked_at.is_(None),
        )
    ).mappings().first()
    if not member:
        raise GovernanceError("INSTITUTION_SCOPE_FORBIDDEN", status_code=403)
    return dict(inst)


def _parse_time_to_minutes(val: str, field_name: str = "time") -> tuple[str, int]:
    cleaned = str(val or "").strip()
    m = TIME_RE.match(cleaned)
    if not m:
        raise GovernanceError(f"INVALID_TIMETABLE_{field_name.upper()}_FORMAT", status_code=422)
    hh = int(m.group(1))
    mm = int(m.group(2))
    total = hh * 60 + mm
    return f"{hh:02d}:{mm:02d}", total


def _minutes_to_hhmm(minutes: int) -> str:
    hh = max(0, min(24, minutes // 60))
    mm = max(0, min(59, minutes % 60))
    if minutes == 1440:
        return "24:00"
    return f"{hh:02d}:{mm:02d}"


def _parse_weekday(val: Any) -> int:
    key = str(val if val is not None else "").strip().lower()
    if key in WEEKDAY_LOOKUP:
        return WEEKDAY_LOOKUP[key]
    raise GovernanceError("INVALID_TIMETABLE_WEEKDAY", status_code=422)


def _normalize_lesson_type(val: Any) -> str:
    raw = str(val or "MA'RUZA").strip().upper().replace("‘", "'").replace("’", "'")
    if raw in ("MARUZA", "MA'RUZA", "LECTURE"):
        return "MA'RUZA"
    if raw in ("AMALIY", "AMALIYOT", "PRACTICE"):
        return "AMALIYOT"
    if raw in ("LAB", "LABORATORIYA", "LABORATORY"):
        return "LABORATORIYA"
    if raw in ("SEMINAR", "WORKSHOP"):
        return "SEMINAR"
    return "MA'RUZA"


def _normalize_and_validate_slots(raw_slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(raw_slots, list):
        raise GovernanceError("INVALID_TIMETABLE_SLOTS_LIST", status_code=422)
    if len(raw_slots) > 500:
        raise GovernanceError("TIMETABLE_SLOTS_LIMIT_EXCEEDED", status_code=422)

    normalized: list[dict[str, Any]] = []
    # Track intervals per (group_code, weekday) to detect overlaps
    by_group_day: dict[tuple[str, int], list[tuple[int, int, str]]] = defaultdict(list)

    for idx, item in enumerate(raw_slots, start=1):
        if not isinstance(item, dict):
            raise GovernanceError(f"INVALID_TIMETABLE_ROW_{idx}", status_code=422)

        group_code = str(item.get("group_code") or "").strip().upper()
        if not 2 <= len(group_code) <= 60:
            raise GovernanceError("INVALID_TIMETABLE_GROUP_CODE", status_code=422)

        subject_name = str(item.get("subject_name") or "").strip()
        if not 2 <= len(subject_name) <= 200:
            raise GovernanceError("INVALID_TIMETABLE_SUBJECT_NAME", status_code=422)

        weekday = _parse_weekday(item.get("weekday"))

        para_raw = item.get("para_number")
        para_number: int | None = None
        if para_raw is not None and str(para_raw).strip() != "":
            try:
                para_number = int(str(para_raw).strip())
                if not 1 <= para_number <= 8:
                    raise ValueError
            except ValueError as exc:
                raise GovernanceError("INVALID_TIMETABLE_PARA_NUMBER", status_code=422) from exc

        start_raw = str(item.get("start_time") or "").strip()
        end_raw = str(item.get("end_time") or "").strip()
        if (not start_raw or not end_raw) and para_number in PARA_PRESETS:
            start_raw, end_raw = PARA_PRESETS[para_number]

        start_time, start_minute = _parse_time_to_minutes(start_raw, "start_time")
        end_time, end_minute = _parse_time_to_minutes(end_raw, "end_time")

        if start_minute >= end_minute or start_minute < 360 or end_minute > 1380:
            raise GovernanceError("INVALID_TIMETABLE_TIME_RANGE", status_code=422)

        # Check overlap within the same (group_code, weekday)
        existing_for_day = by_group_day[(group_code, weekday)]
        for ex_start, ex_end, ex_subj in existing_for_day:
            if ranges_overlap(start_minute, end_minute, ex_start, ex_end):
                raise GovernanceError("TIMETABLE_SLOT_OVERLAP", status_code=422)
        existing_for_day.append((start_minute, end_minute, subject_name))

        normalized.append(
            {
                "id": str(item.get("id") or uuid4()),
                "group_code": group_code,
                "program_name": str(item.get("program_name") or "Bakalavriat").strip()[:160],
                "study_year": str(item.get("study_year") or "4-kurs").strip()[:40],
                "weekday": weekday,
                "weekday_name": WEEKDAY_NAMES_UZ[weekday],
                "para_number": para_number or 1,
                "start_time": start_time,
                "end_time": end_time,
                "start_minute": start_minute,
                "end_minute": end_minute,
                "subject_name": subject_name,
                "lesson_type": _normalize_lesson_type(item.get("lesson_type")),
                "room": str(item.get("room") or "Auditoriya").strip()[:60],
                "teacher_name": str(item.get("teacher_name") or "").strip()[:160],
            }
        )

    normalized.sort(key=lambda s: (s["group_code"], s["weekday"], s["start_minute"]))
    return normalized


def _compute_free_work_windows(
    slots: list[dict[str, Any]],
    commute_buffer_minutes: int = 30,
    workday_start_minute: int = 480,  # 08:00
    workday_end_minute: int = 1200,   # 20:00
) -> dict[str, list[dict[str, Any]]]:
    """Compute available student work intervals per group & weekday by subtracting class hours from [08:00, 20:00)."""
    groups = sorted({s["group_code"] for s in slots}) or ["DEFAULT"]
    result: dict[str, list[dict[str, Any]]] = {}

    for grp in groups:
        grp_slots = [s for s in slots if s["group_code"] == grp]
        day_windows: list[dict[str, Any]] = []
        for wd in range(1, 7):  # Monday..Saturday
            free_ivs: list[tuple[int, int]] = [(workday_start_minute, workday_end_minute)]
            day_classes = [s for s in grp_slots if s["weekday"] == wd]
            for cl in day_classes:
                b_start = max(0, int(cl["start_minute"]) - commute_buffer_minutes)
                b_end = min(1440, int(cl["end_minute"]) + commute_buffer_minutes)
                free_ivs = subtract_interval(free_ivs, b_start, b_end)
            # Keep work windows that are at least 90 minutes long
            valid_ivs = [(a, b) for a, b in merge_adjacent_intervals(free_ivs) if (b - a) >= 90]
            day_windows.append(
                {
                    "weekday": wd,
                    "weekday_name": WEEKDAY_NAMES_UZ[wd],
                    "class_count": len(day_classes),
                    "free_intervals": [
                        {
                            "start_minute": a,
                            "end_minute": b,
                            "start_time": _minutes_to_hhmm(a),
                            "end_time": _minutes_to_hhmm(b),
                            "duration_minutes": b - a,
                        }
                        for a, b in valid_ivs
                    ],
                }
            )
        result[grp] = day_windows
    return result


def _sync_enrolled_students_availability(
    conn: Any,
    inst_id: str,
    slots: list[dict[str, Any]],
    commute_buffer_minutes: int = 30,
) -> int:
    """Synchronize `flexbridge.availability_rules` for students enrolled in `inst_id`."""
    if not slots:
        return 0

    free_by_group = _compute_free_work_windows(slots, commute_buffer_minutes=commute_buffer_minutes)
    default_group = next(iter(free_by_group.keys()))

    t_enr = table("enrollments")
    t_rules = table("availability_rules")
    t_cand = table("candidate_profiles")

    enrollments = conn.execute(
        select(t_enr.c.candidate_id, t_enr.c.program).where(
            t_enr.c.institution_id == inst_id,
            t_enr.c.end_date.is_(None),
        )
    ).mappings().all()

    seen_candidates: set[str] = set()
    today = local_today()

    for row in enrollments:
        cand_id = str(row["candidate_id"])
        if cand_id in seen_candidates:
            continue
        seen_candidates.add(cand_id)

        prog = str(row.get("program") or "").strip().upper()
        matched_group = default_group
        for grp in free_by_group:
            if grp in prog or any(
                s["group_code"] == grp and s["program_name"].upper() in prog for s in slots
            ):
                matched_group = grp
                break

        day_windows = free_by_group[matched_group]
        conn.execute(t_rules.delete().where(t_rules.c.candidate_id == cand_id))

        for dw in day_windows:
            wd = int(dw["weekday"])
            for iv in dw["free_intervals"]:
                insert_row(
                    conn,
                    "availability_rules",
                    candidate_id=cand_id,
                    weekday=wd,
                    valid_from=today,
                    valid_to=None,
                    timezone="Asia/Tashkent",
                    start_minute=int(iv["start_minute"]),
                    end_minute=int(iv["end_minute"]),
                )

        conn.execute(
            t_cand.update().where(t_cand.c.id == cand_id).values(updated_at=now())
        )

    return len(seen_candidates)


def _parse_csv_content(raw_text: str) -> list[dict[str, Any]]:
    text_clean = raw_text.lstrip("\ufeff").strip()
    if not text_clean:
        raise GovernanceError("EMPTY_TIMETABLE_TEMPLATE_FILE", status_code=422)

    lines = [ln for ln in text_clean.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if len(lines) < 2:
        raise GovernanceError("EMPTY_TIMETABLE_TEMPLATE_ROWS", status_code=422)

    header_line = lines[0]
    delimiter = ";" if header_line.count(";") > header_line.count(",") else ","
    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=delimiter)

    if not reader.fieldnames:
        raise GovernanceError("INVALID_TIMETABLE_CSV_HEADER", status_code=422)

    normalized_headers = {h.strip().lower() for h in reader.fieldnames if h}
    required = {"group_code", "weekday", "subject_name"}
    if not required.issubset(normalized_headers):
        raise GovernanceError("MISSING_REQUIRED_TIMETABLE_COLUMNS", status_code=422)

    rows: list[dict[str, Any]] = []
    for raw_row in reader:
        clean_row = {str(k or "").strip().lower(): (v or "").strip() for k, v in raw_row.items()}
        if not any(clean_row.values()):
            continue
        rows.append(clean_row)

    if not rows:
        raise GovernanceError("EMPTY_TIMETABLE_TEMPLATE_ROWS", status_code=422)
    return rows


class UniversityTimetableService:
    def get_timetable(
        self,
        actor: ActorContext,
        inst_id: str,
        group_code: str | None = None,
    ) -> dict[str, Any]:
        with transaction() as conn:
            inst = _verify_institution_staff(conn, actor, inst_id)
            stored = load_domain_record(TIMETABLE_NAMESPACE, str(inst_id)) or {}

        all_slots: list[dict[str, Any]] = stored.get("slots") if isinstance(stored.get("slots"), list) else []
        commute_buffer = int(stored.get("commute_buffer_minutes") or 30)
        groups = sorted({s.get("group_code", "") for s in all_slots if s.get("group_code")})

        if group_code and group_code.strip():
            target_group = group_code.strip().upper()
            filtered_slots = [s for s in all_slots if s.get("group_code") == target_group]
        else:
            filtered_slots = all_slots

        free_windows = _compute_free_work_windows(filtered_slots, commute_buffer_minutes=commute_buffer) if filtered_slots else {}

        return {
            "ok": True,
            "contract_id": "API-098-TIMETABLE",
            "institution_id": str(inst_id),
            "institution_name": inst.get("name", ""),
            "academic_semester": stored.get("academic_semester") or "2026-2027 Kuzgi semestr",
            "commute_buffer_minutes": commute_buffer,
            "groups": groups,
            "total_slots": len(all_slots),
            "slots": filtered_slots,
            "computed_free_windows": free_windows,
            "students_synced_count": int(stored.get("students_synced_count") or 0),
            "updated_at": stored.get("updated_at"),
            "para_presets": [
                {"para_number": k, "start_time": v[0], "end_time": v[1]}
                for k, v in sorted(PARA_PRESETS.items())
            ],
        }

    def save_manual_timetable(
        self,
        actor: ActorContext,
        inst_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Save manually entered timetable slots (or append/remove a slot) and sync student work availability."""
        with transaction() as conn:
            _verify_institution_staff(conn, actor, inst_id)
            current = load_domain_record(TIMETABLE_NAMESPACE, str(inst_id)) or {}
            existing_slots: list[dict[str, Any]] = (
                current.get("slots") if isinstance(current.get("slots"), list) else []
            )

            mode = str(payload.get("mode") or "REPLACE").upper().strip()
            raw_slots = payload.get("slots")

            if mode == "APPEND" and isinstance(payload.get("slot"), dict):
                candidate_slots = existing_slots + [payload["slot"]]
            elif mode == "DELETE_SLOT" and payload.get("slot_id"):
                target_id = str(payload["slot_id"]).strip()
                candidate_slots = [s for s in existing_slots if str(s.get("id")) != target_id]
            elif isinstance(raw_slots, list):
                if mode == "MERGE_GROUP" and payload.get("group_code"):
                    target_grp = str(payload["group_code"]).strip().upper()
                    kept = [s for s in existing_slots if s.get("group_code") != target_grp]
                    candidate_slots = kept + raw_slots
                else:
                    candidate_slots = raw_slots
            else:
                raise GovernanceError("INVALID_TIMETABLE_PAYLOAD", status_code=422)

            validated_slots = _normalize_and_validate_slots(candidate_slots)
            commute_buffer = max(0, min(120, int(payload.get("commute_buffer_minutes") or current.get("commute_buffer_minutes") or 30)))
            semester = str(payload.get("academic_semester") or current.get("academic_semester") or "2026-2027 Kuzgi semestr").strip()[:120]
            sync_flag = bool(payload.get("sync_student_availability", True))

            synced_count = int(current.get("students_synced_count") or 0)
            if sync_flag and validated_slots:
                synced_count = _sync_enrolled_students_availability(
                    conn, str(inst_id), validated_slots, commute_buffer_minutes=commute_buffer
                )

            ts = now().isoformat()
            updated_record = {
                "institution_id": str(inst_id),
                "academic_semester": semester,
                "commute_buffer_minutes": commute_buffer,
                "slots": validated_slots,
                "students_synced_count": synced_count,
                "updated_at": ts,
            }
            save_domain_record(TIMETABLE_NAMESPACE, str(inst_id), updated_record)

            audit.append_audit_event(
                actor_id=actor.user_id,
                action="INSTITUTION_TIMETABLE_MANUAL_SAVE",
                entity_type="institution",
                entity_id=str(inst_id),
                metadata={
                    "mode": mode,
                    "slots_count": len(validated_slots),
                    "groups_count": len({s["group_code"] for s in validated_slots}),
                    "students_synced_count": synced_count,
                },
            )

        return self.get_timetable(actor, inst_id)

    def get_template_specification(
        self,
        actor: ActorContext,
        inst_id: str,
        template_format: str = "CSV",
    ) -> dict[str, Any]:
        """Return official downloadable CSV and JSON timetable templates for University staff."""
        with transaction() as conn:
            inst = _verify_institution_staff(conn, actor, inst_id)

        fmt = str(template_format or "CSV").upper().strip()
        csv_buf = io.StringIO()
        writer = csv.DictWriter(csv_buf, fieldnames=CSV_TEMPLATE_COLUMNS)
        writer.writeheader()
        for row in SAMPLE_TEMPLATE_ROWS:
            writer.writerow(row)
        csv_content = csv_buf.getvalue()

        json_content = json.dumps(
            {
                "schema_version": "1.4",
                "academic_semester": "2026-2027 Kuzgi semestr",
                "commute_buffer_minutes": 30,
                "columns": CSV_TEMPLATE_COLUMNS,
                "slots": SAMPLE_TEMPLATE_ROWS,
            },
            indent=2,
            ensure_ascii=False,
        )

        return {
            "ok": True,
            "contract_id": "API-098-TIMETABLE-TEMPLATE",
            "institution_id": str(inst_id),
            "institution_name": inst.get("name", ""),
            "format": fmt,
            "filename": "flexbridge_otm_dars_jadvali_shablon.json" if fmt == "JSON" else "flexbridge_otm_dars_jadvali_shablon.csv",
            "columns": CSV_TEMPLATE_COLUMNS,
            "allowed_lesson_types": sorted(ALLOWED_LESSON_TYPES),
            "para_presets": [
                {"para_number": k, "start_time": v[0], "end_time": v[1]}
                for k, v in sorted(PARA_PRESETS.items())
            ],
            "csv_template": csv_content,
            "json_template": json_content,
            "sample_rows": SAMPLE_TEMPLATE_ROWS,
        }

    def import_timetable_from_template(
        self,
        actor: ActorContext,
        inst_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Parse, validate, and import a CSV or JSON schedule template uploaded by University staff."""
        with transaction() as conn:
            _verify_institution_staff(conn, actor, inst_id)
            current = load_domain_record(TIMETABLE_NAMESPACE, str(inst_id)) or {}
            existing_slots: list[dict[str, Any]] = (
                current.get("slots") if isinstance(current.get("slots"), list) else []
            )

            fmt = str(payload.get("format") or "CSV").upper().strip()
            raw_content = payload.get("content")
            content_b64 = payload.get("content_base64")

            if content_b64 and not raw_content:
                try:
                    if "," in str(content_b64) and str(content_b64).startswith("data:"):
                        content_b64 = str(content_b64).split(",", 1)[1]
                    raw_content = base64.b64decode(content_b64).decode("utf-8-sig")
                except Exception as exc:
                    raise GovernanceError("INVALID_TIMETABLE_FILE_ENCODING", status_code=422) from exc

            if not raw_content or not str(raw_content).strip():
                raise GovernanceError("EMPTY_TIMETABLE_TEMPLATE_FILE", status_code=422)

            text_content = str(raw_content).strip()
            if fmt == "JSON" or text_content.startswith("{") or text_content.startswith("["):
                try:
                    parsed_json = json.loads(text_content)
                except Exception as exc:
                    raise GovernanceError("INVALID_TIMETABLE_JSON_SYNTAX", status_code=422) from exc
                if isinstance(parsed_json, dict):
                    imported_raw_rows = parsed_json.get("slots") or parsed_json.get("items") or []
                elif isinstance(parsed_json, list):
                    imported_raw_rows = parsed_json
                else:
                    raise GovernanceError("INVALID_TIMETABLE_JSON_STRUCTURE", status_code=422)
            else:
                imported_raw_rows = _parse_csv_content(text_content)

            validated_imported = _normalize_and_validate_slots(imported_raw_rows)

            replace_existing = bool(payload.get("replace_existing", True))
            if replace_existing:
                final_slots = validated_imported
            else:
                imported_groups = {s["group_code"] for s in validated_imported}
                kept = [s for s in existing_slots if s.get("group_code") not in imported_groups]
                final_slots = _normalize_and_validate_slots(kept + validated_imported)

            commute_buffer = max(
                0,
                min(120, int(payload.get("commute_buffer_minutes") or current.get("commute_buffer_minutes") or 30)),
            )
            semester = str(
                payload.get("academic_semester") or current.get("academic_semester") or "2026-2027 Kuzgi semestr"
            ).strip()[:120]
            sync_flag = bool(payload.get("sync_student_availability", True))

            synced_count = int(current.get("students_synced_count") or 0)
            if sync_flag and final_slots:
                synced_count = _sync_enrolled_students_availability(
                    conn, str(inst_id), final_slots, commute_buffer_minutes=commute_buffer
                )

            ts = now().isoformat()
            updated_record = {
                "institution_id": str(inst_id),
                "academic_semester": semester,
                "commute_buffer_minutes": commute_buffer,
                "slots": final_slots,
                "students_synced_count": synced_count,
                "updated_at": ts,
            }
            save_domain_record(TIMETABLE_NAMESPACE, str(inst_id), updated_record)

            groups_updated = sorted({s["group_code"] for s in validated_imported})
            audit.append_audit_event(
                actor_id=actor.user_id,
                action="INSTITUTION_TIMETABLE_TEMPLATE_IMPORT",
                entity_type="institution",
                entity_id=str(inst_id),
                metadata={
                    "format": fmt,
                    "imported_slots_count": len(validated_imported),
                    "total_slots_count": len(final_slots),
                    "groups_updated": groups_updated,
                    "students_synced_count": synced_count,
                },
            )

        state = self.get_timetable(actor, inst_id)
        return {
            **state,
            "imported_count": len(validated_imported),
            "groups_updated": groups_updated,
        }


university_timetable_service = UniversityTimetableService()

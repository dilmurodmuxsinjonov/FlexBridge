"""University Portal Analytics calculation and aggregation engine (Milestone 3 / API-125).

Provides production-grade analytics across three analytical pillars:
1. Talabalar davomati (student attendance monitoring, rates, risk categorization, day-type breakdown, late submissions).
2. Haftalik soatlar monitoringi (weekly logged hours, ISO week trends, program & employer breakdowns, O'zR MK 118 statutory compliance alerts).
3. Amaliyot natijalari tahlili (internship status breakdown, completion rate %, academic review conclusions, mentor workplace evaluations).

Enforces strict INSTITUTION scoping, COORDINATOR role authorization, anti-enumeration uniform 404 IDOR defense,
and atomic SQL queries with CTEs. Zero new DDL or schema migrations.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, text

from app.api.dependencies import ActorContext
from app.db.storage import table, transaction
from app.services.authority import institution_role_authority
from app.services.governance import GovernanceError


class UniversityAnalyticsError(Exception):
    def __init__(self, code: str, status_code: int = 400, message: str | None = None):
        super().__init__(message or code)
        self.code = code
        self.status_code = status_code
        self.message = message or code


class UniversityAnalyticsService:
    def get_institution_analytics(
        self,
        *,
        actor: ActorContext,
        institution_id: str | UUID,
        program: str | None = None,
        organization_id: str | UUID | None = None,
        status: str | None = None,
        from_date: str | date | None = None,
        to_date: str | date | None = None,
    ) -> dict[str, Any]:
        """Aggregate institution analytics across attendance, weekly hours, and internship results (API-125)."""
        # 1. UUID & parameter normalization
        try:
            inst_uuid = UUID(str(institution_id))
            str_inst_id = str(inst_uuid)
        except (ValueError, TypeError):
            raise UniversityAnalyticsError("INSTITUTION_NOT_FOUND", status_code=404)

        clean_org_id: str | None = None
        if organization_id:
            try:
                clean_org_id = str(UUID(str(organization_id)))
            except (ValueError, TypeError):
                raise UniversityAnalyticsError("INVALID_ORGANIZATION_ID", status_code=422)

        clean_program = str(program).strip() if program else None
        clean_status = str(status).strip().upper() if status else None

        clean_from_date: str | None = None
        if from_date:
            try:
                clean_from_date = str(from_date).strip()[:10]
                date.fromisoformat(clean_from_date)
            except (ValueError, TypeError):
                raise UniversityAnalyticsError("INVALID_DATE_FORMAT", status_code=422)

        clean_to_date: str | None = None
        if to_date:
            try:
                clean_to_date = str(to_date).strip()[:10]
                date.fromisoformat(clean_to_date)
            except (ValueError, TypeError):
                raise UniversityAnalyticsError("INVALID_DATE_FORMAT", status_code=422)

        with transaction() as conn:
            # 2. Anti-enumeration existence and verification check
            t_inst = table("institutions")
            inst = conn.execute(
                select(t_inst).where(t_inst.c.id == str_inst_id)
            ).mappings().first()
            if not inst or inst.get("status") != "VERIFIED":
                raise UniversityAnalyticsError("INSTITUTION_NOT_FOUND", status_code=404)

            # 3. Cross-tenant anti-enumeration & COORDINATOR authorization check
            t_mem = table("institution_memberships")
            mem_row = conn.execute(
                select(t_mem.c.id).where(
                    t_mem.c.institution_id == str_inst_id,
                    t_mem.c.user_id == actor.user_id,
                    t_mem.c.status == "ACTIVE",
                    t_mem.c.revoked_at.is_(None),
                )
            ).first()

            from app.services.auth import roles_for
            actor_roles = roles_for(conn, actor.user_id)
            is_platform_admin = bool({"ADMIN", "OPERATOR"}.intersection(actor_roles))

            if not is_platform_admin and not mem_row:
                raise UniversityAnalyticsError("INSTITUTION_NOT_FOUND", status_code=404)

            if not is_platform_admin:
                try:
                    institution_role_authority(conn, actor.user_id, str_inst_id, "COORDINATOR")
                except GovernanceError as exc:
                    raise UniversityAnalyticsError(exc.code, status_code=exc.status_code) from exc

            # 4. Atomic CTE Query: Fetch Placements and Calculate Expected Working Days
            # Expected days: Monday-Saturday dates within placement start_date and LEAST(end_date, CURRENT_DATE)
            placements_sql = text("""
            SELECT
                fp.placement_id,
                fp.candidate_id,
                fp.program,
                fp.candidate_name,
                fp.organization_name,
                fp.placement_status,
                fp.start_date,
                fp.end_date,
                fp.weekly_limit_minutes,
                fp.daily_limit_minutes,
                COALESCE(
                    CASE
                        WHEN eff_start IS NOT NULL AND eff_end IS NOT NULL AND eff_start <= eff_end THEN (
                            SELECT COUNT(*)::int
                            FROM generate_series(eff_start::timestamp, eff_end::timestamp, '1 day'::interval) d
                            WHERE EXTRACT(ISODOW FROM d) <= 6
                        )
                        ELSE 0
                    END, 0
                ) AS expected_working_days
            FROM (
                SELECT
                    p.id AS placement_id,
                    p.candidate_id,
                    p.organization_id,
                    p.enrollment_id,
                    p.academic_track,
                    p.status AS placement_status,
                    p.start_date,
                    p.end_date,
                    COALESCE(en.program, 'Noma''lum dastur') AS program,
                    COALESCE(u.display_name, 'Talaba') AS candidate_name,
                    COALESCE(org.public_name, org.legal_name, 'Tashkilot') AS organization_name,
                    COALESCE(pt.weekly_limit_minutes, 2400) AS weekly_limit_minutes,
                    COALESCE(pt.daily_limit_minutes, 480) AS daily_limit_minutes,
                    GREATEST(p.start_date, COALESCE(CAST(:from_date AS date), p.start_date)) AS eff_start,
                    LEAST(COALESCE(p.end_date, CURRENT_DATE), CURRENT_DATE, COALESCE(CAST(:to_date AS date), CURRENT_DATE)) AS eff_end
                FROM flexbridge.placements p
                LEFT JOIN flexbridge.enrollments en ON en.id = p.enrollment_id
                LEFT JOIN flexbridge.candidate_profiles cp ON cp.id = p.candidate_id
                LEFT JOIN flexbridge.users u ON u.id = cp.user_id
                LEFT JOIN flexbridge.organizations org ON org.id = p.organization_id
                LEFT JOIN flexbridge.placement_terms pt ON pt.id = p.current_terms_id
                WHERE (
                    p.enrollment_id IN (SELECT id FROM flexbridge.enrollments WHERE institution_id = CAST(:inst AS uuid))
                    OR p.id IN (SELECT placement_id FROM flexbridge.placement_academic_bindings WHERE institution_id = CAST(:inst AS uuid))
                    OR p.id IN (SELECT placement_id FROM flexbridge.student_academic_requests WHERE institution_id = CAST(:inst AS uuid))
                    OR p.id IN (SELECT placement_id FROM flexbridge.academic_assignments WHERE institution_id = CAST(:inst AS uuid))
                )
                AND (CAST(:program AS text) IS NULL OR en.program = CAST(:program AS text))
                AND (CAST(:org_id AS uuid) IS NULL OR p.organization_id = CAST(:org_id AS uuid))
                AND (CAST(:status AS text) IS NULL OR p.status = CAST(:status AS text))
            ) fp
            ORDER BY fp.candidate_name ASC;
            """)

            placement_rows = conn.execute(
                placements_sql,
                {
                    "inst": str_inst_id,
                    "program": clean_program,
                    "org_id": clean_org_id,
                    "status": clean_status,
                    "from_date": clean_from_date,
                    "to_date": clean_to_date,
                },
            ).mappings().all()

            placement_ids = [str(r["placement_id"]) for r in placement_rows]

            # 5. Empty Placement Guard
            if not placement_ids:
                return {
                    "institution_id": str_inst_id,
                    "institution_name": inst["name"],
                    "registry_code": inst.get("registry_code"),
                    "summary": {
                        "total_students": 0,
                        "active_interns": 0,
                        "completed_interns": 0,
                        "overall_attendance_rate": 0.0,
                        "total_logged_hours": 0.0,
                        "avg_weekly_hours_per_student": 0.0,
                        "completion_rate": 0.0,
                        "pending_teacher_reviews": 0,
                        "academic_conclusions_count": 0,
                    },
                    "attendance_metrics": {
                        "overall_rate": 0.0,
                        "by_status_distribution": {
                            "good": 0,
                            "warning": 0,
                            "critical": 0,
                        },
                        "by_day_type": {
                            "work": 0,
                            "remote_work": 0,
                            "sick_leave": 0,
                            "absence": 0,
                            "holiday": 0,
                        },
                        "late_submissions_count": 0,
                        "students": [],
                    },
                    "weekly_hours_monitoring": {
                        "current_week_hours": 0.0,
                        "avg_weekly_hours": 0.0,
                        "weekly_trend": [],
                        "by_program": [],
                        "by_organization": [],
                        "compliance_alerts": {
                            "overtime_students": 0,
                            "zero_hours_this_week": 0,
                        },
                    },
                    "internship_results": {
                        "total_placements": 0,
                        "by_status": {},
                        "completion_rate": 0.0,
                        "academic_conclusions": {
                            "total": 0,
                            "complete": 0,
                            "revision_required": 0,
                            "pending": 0,
                        },
                        "workplace_evaluations": {
                            "approved_rate": 100.0,
                            "approved_count": 0,
                            "changes_requested_count": 0,
                            "rejected_count": 0,
                        },
                        "program_performance": [],
                    },
                }

            # 6. Fetch Logs for Institution Placements
            logs_sql = text("""
            SELECT
                dl.placement_id,
                dl.local_date,
                lr.id AS revision_id,
                lr.day_type,
                lr.total_minutes,
                lr.submitted_at,
                (CAST(lr.submitted_at AS date) - dl.local_date) AS days_to_submit,
                TO_CHAR(dl.local_date, 'IYYY-"W"IW') AS iso_week
            FROM flexbridge.daily_logs dl
            JOIN flexbridge.log_revisions lr ON lr.id = dl.current_revision_id
            WHERE dl.placement_id = ANY(:placement_ids)
              AND lr.submitted_at IS NOT NULL
              AND (CAST(:from_date AS date) IS NULL OR dl.local_date >= CAST(:from_date AS date))
              AND (CAST(:to_date AS date) IS NULL OR dl.local_date <= CAST(:to_date AS date))
            ORDER BY dl.local_date ASC;
            """)

            log_rows = conn.execute(
                logs_sql,
                {
                    "placement_ids": placement_ids,
                    "from_date": clean_from_date,
                    "to_date": clean_to_date,
                },
            ).mappings().all()

            # 7. Fetch Academic Conclusions (academic_decision_proofs and placement_decisions)
            conclusions_sql = text("""
            SELECT
                adp.placement_id,
                COALESCE(adp.receipt->>'decision', pd.decision) AS decision
            FROM flexbridge.academic_decision_proofs adp
            LEFT JOIN flexbridge.placement_decisions pd ON pd.id = adp.decision_id
            WHERE adp.placement_id = ANY(:placement_ids)
            UNION
            SELECT
                pd.placement_id,
                pd.decision
            FROM flexbridge.placement_decisions pd
            WHERE pd.placement_id = ANY(:placement_ids)
              AND pd.side = 'TEACHER';
            """)

            conclusion_rows = conn.execute(
                conclusions_sql,
                {"placement_ids": placement_ids},
            ).mappings().all()

            # 8. Fetch Workplace Evaluations (workplace_log_reviews)
            evaluations_sql = text("""
            SELECT
                wlr.decision,
                COUNT(*)::int AS cnt
            FROM flexbridge.workplace_log_reviews wlr
            WHERE wlr.placement_id = ANY(:placement_ids)
            GROUP BY wlr.decision;
            """)

            evaluation_rows = conn.execute(
                evaluations_sql,
                {"placement_ids": placement_ids},
            ).mappings().all()

            # 9. Fetch Pending Teacher Reviews Count
            pending_reviews_sql = text("""
            SELECT COUNT(*)::int
            FROM flexbridge.daily_logs dl
            JOIN flexbridge.log_revisions lr ON lr.id = dl.current_revision_id
            WHERE dl.placement_id = ANY(:placement_ids)
              AND lr.submitted_at IS NOT NULL
              AND lr.id NOT IN (
                  SELECT revision_id FROM flexbridge.academic_log_reviews WHERE placement_id = ANY(:placement_ids)
              );
            """)

            pending_teacher_reviews_count = conn.execute(
                pending_reviews_sql,
                {"placement_ids": placement_ids},
            ).scalar() or 0

            # -------------------------------------------------------------
            # Aggregation: Pillar 1 — Talabalar Davomati
            # -------------------------------------------------------------
            # Map logs by placement_id
            logs_by_placement: dict[str, list[Any]] = {pid: [] for pid in placement_ids}
            for l_row in log_rows:
                pid = str(l_row["placement_id"])
                if pid in logs_by_placement:
                    logs_by_placement[pid].append(l_row)

            day_type_counts = {
                "work": 0,
                "remote_work": 0,
                "sick_leave": 0,
                "absence": 0,
                "holiday": 0,
            }
            late_submissions_count = 0

            for l_row in log_rows:
                dtype = str(l_row["day_type"]).upper()
                if dtype == "WORK":
                    day_type_counts["work"] += 1
                elif dtype == "REMOTE_WORK":
                    day_type_counts["remote_work"] += 1
                elif dtype == "SICK_LEAVE":
                    day_type_counts["sick_leave"] += 1
                elif dtype == "ABSENCE":
                    day_type_counts["absence"] += 1
                elif dtype == "HOLIDAY":
                    day_type_counts["holiday"] += 1

                days_to_sub = l_row["days_to_submit"]
                if days_to_sub is not None and days_to_sub > 3:
                    late_submissions_count += 1

            students_list: list[dict[str, Any]] = []
            status_dist = {"good": 0, "warning": 0, "critical": 0}

            total_inst_expected_days = 0
            total_inst_attended_days = 0

            # For compliance alerts (overtime and zero-hours)
            current_utc = datetime.now(timezone.utc)
            # Standard ISO week format: e.g. "2026-W46"
            current_iso_week = f"{current_utc.isocalendar()[0]}-W{current_utc.isocalendar()[1]:02d}"

            student_weekly_minutes: dict[str, dict[str, int]] = {}
            overtime_candidates: set[str] = set()
            active_candidate_ids: set[str] = set()
            active_candidates_with_hours_this_week: set[str] = set()

            for p_row in placement_rows:
                pid = str(p_row["placement_id"])
                cid = str(p_row["candidate_id"])
                expected_days = int(p_row["expected_working_days"])
                total_inst_expected_days += expected_days

                if p_row["placement_status"] == "ACTIVE":
                    active_candidate_ids.add(cid)

                p_logs = logs_by_placement.get(pid, [])
                attended_dates: set[str] = set()
                sick_dates: set[str] = set()
                absence_dates: set[str] = set()
                holiday_dates: set[str] = set()

                if cid not in student_weekly_minutes:
                    student_weekly_minutes[cid] = {}

                for l in p_logs:
                    dtype = str(l["day_type"]).upper()
                    ldate = str(l["local_date"])
                    mins = int(l["total_minutes"] or 0)
                    iso_wk = str(l["iso_week"])

                    student_weekly_minutes[cid][iso_wk] = student_weekly_minutes[cid].get(iso_wk, 0) + mins

                    if iso_wk == current_iso_week and mins > 0:
                        active_candidates_with_hours_this_week.add(cid)

                    # Overtime check under O'zR MK 118-modda: daily > 480 or weekly limit exceeded
                    if mins > int(p_row["daily_limit_minutes"]):
                        overtime_candidates.add(cid)

                    if dtype in ("WORK", "REMOTE_WORK"):
                        attended_dates.add(ldate)
                    elif dtype == "SICK_LEAVE":
                        sick_dates.add(ldate)
                    elif dtype == "ABSENCE":
                        absence_dates.add(ldate)
                    elif dtype == "HOLIDAY":
                        holiday_dates.add(ldate)

                # Check weekly limits for this candidate
                for wk, wk_mins in student_weekly_minutes[cid].items():
                    if wk_mins > int(p_row["weekly_limit_minutes"]):
                        overtime_candidates.add(cid)

                attended_days = len(attended_dates)
                sick_days = len(sick_dates)
                holiday_days = len(holiday_dates)
                absence_logs_count = len(absence_dates)

                total_inst_attended_days += attended_days

                # Absent days: explicit absence logs or unlogged expected days
                absent_days = max(
                    absence_logs_count,
                    max(0, expected_days - attended_days - sick_days - holiday_days),
                )

                if expected_days > 0:
                    att_rate = round((attended_days / expected_days) * 100.0, 1)
                else:
                    att_rate = 100.0 if attended_days > 0 else 100.0

                if att_rate >= 85.0:
                    att_status = "GOOD"
                    status_dist["good"] += 1
                elif att_rate >= 70.0:
                    att_status = "WARNING"
                    status_dist["warning"] += 1
                else:
                    att_status = "CRITICAL"
                    status_dist["critical"] += 1

                students_list.append({
                    "student_id": cid,
                    "student_name": p_row["candidate_name"],
                    "program": p_row["program"],
                    "organization_name": p_row["organization_name"],
                    "placement_id": pid,
                    "expected_days": expected_days,
                    "attended_days": attended_days,
                    "absent_days": absent_days,
                    "sick_days": sick_days,
                    "attendance_rate": att_rate,
                    "attendance_status": att_status,
                })

            overall_attendance_rate = (
                round((total_inst_attended_days / total_inst_expected_days) * 100.0, 1)
                if total_inst_expected_days > 0
                else 0.0
            )

            # -------------------------------------------------------------
            # Aggregation: Pillar 2 — Haftalik Soatlar Monitoringi
            # -------------------------------------------------------------
            weekly_aggregates: dict[str, dict[str, Any]] = {}
            total_logged_minutes = 0

            # Program hours mapping
            program_minutes: dict[str, int] = {}
            program_students: dict[str, set[str]] = {}

            # Organization hours mapping
            org_minutes: dict[str, int] = {}
            org_students: dict[str, set[str]] = {}

            # Map placement to program and org
            p_to_prog = {str(r["placement_id"]): str(r["program"]) for r in placement_rows}
            p_to_org = {str(r["placement_id"]): str(r["organization_name"]) for r in placement_rows}
            p_to_cid = {str(r["placement_id"]): str(r["candidate_id"]) for r in placement_rows}

            for p_row in placement_rows:
                prog = str(p_row["program"])
                org = str(p_row["organization_name"])
                cid = str(p_row["candidate_id"])

                if prog not in program_minutes:
                    program_minutes[prog] = 0
                    program_students[prog] = set()
                program_students[prog].add(cid)

                if org not in org_minutes:
                    org_minutes[org] = 0
                    org_students[org] = set()
                org_students[org].add(cid)

            for l_row in log_rows:
                pid = str(l_row["placement_id"])
                iso_wk = str(l_row["iso_week"])
                mins = int(l_row["total_minutes"] or 0)
                cid = p_to_cid.get(pid, pid)
                prog = p_to_prog.get(pid, "Noma'lum")
                org = p_to_org.get(pid, "Tashkilot")

                total_logged_minutes += mins
                program_minutes[prog] = program_minutes.get(prog, 0) + mins
                org_minutes[org] = org_minutes.get(org, 0) + mins

                if iso_wk not in weekly_aggregates:
                    weekly_aggregates[iso_wk] = {
                        "week": iso_wk,
                        "logged_minutes": 0,
                        "active_candidates": set(),
                    }
                weekly_aggregates[iso_wk]["logged_minutes"] += mins
                if mins > 0:
                    weekly_aggregates[iso_wk]["active_candidates"].add(cid)

            weekly_trend: list[dict[str, Any]] = []
            for wk in sorted(weekly_aggregates.keys()):
                entry = weekly_aggregates[wk]
                weekly_trend.append({
                    "week": wk,
                    "logged_hours": round(entry["logged_minutes"] / 60.0, 1),
                    "active_students": len(entry["active_candidates"]),
                })

            current_week_mins = weekly_aggregates.get(current_iso_week, {}).get("logged_minutes", 0)
            current_week_hours = round(current_week_mins / 60.0, 1)
            total_logged_hours = round(total_logged_minutes / 60.0, 1)

            # Average weekly hours per student
            num_weeks = max(1, len(weekly_trend))
            num_students = max(1, len(students_list))
            avg_weekly_hours_per_student = round(total_logged_hours / (num_students * num_weeks), 1)

            by_program_list: list[dict[str, Any]] = []
            for prog, mins in sorted(program_minutes.items()):
                st_count = len(program_students.get(prog, set()))
                tot_hrs = round(mins / 60.0, 1)
                avg_hrs = round(tot_hrs / max(1, st_count), 1)
                by_program_list.append({
                    "program": prog,
                    "total_hours": tot_hrs,
                    "student_count": st_count,
                    "avg_hours": avg_hrs,
                })

            by_org_list: list[dict[str, Any]] = []
            for org, mins in sorted(org_minutes.items()):
                st_count = len(org_students.get(org, set()))
                by_org_list.append({
                    "organization_name": org,
                    "total_hours": round(mins / 60.0, 1),
                    "intern_count": st_count,
                })

            zero_hours_this_week = len(active_candidate_ids - active_candidates_with_hours_this_week)

            # -------------------------------------------------------------
            # Aggregation: Pillar 3 — Amaliyot Natijalari Tahlili
            # -------------------------------------------------------------
            total_placements = len(placement_rows)
            status_counts: dict[str, int] = {}
            prog_enrolled: dict[str, int] = {}
            prog_completed: dict[str, int] = {}
            prog_active: dict[str, int] = {}

            for p_row in placement_rows:
                pst = str(p_row["placement_status"]).upper()
                status_counts[pst] = status_counts.get(pst, 0) + 1

                prog = str(p_row["program"])
                prog_enrolled[prog] = prog_enrolled.get(prog, 0) + 1
                if pst == "COMPLETED":
                    prog_completed[prog] = prog_completed.get(prog, 0) + 1
                elif pst == "ACTIVE":
                    prog_active[prog] = prog_active.get(prog, 0) + 1

            completed_count = status_counts.get("COMPLETED", 0)
            active_count = status_counts.get("ACTIVE", 0)
            completion_rate = (
                round((completed_count / total_placements) * 100.0, 1)
                if total_placements > 0
                else 0.0
            )

            # Academic Conclusions breakdown
            conclusions_dict = {
                "total": 0,
                "complete": 0,
                "revision_required": 0,
                "pending": 0,
            }
            concluded_pids: set[str] = set()

            for c_row in conclusion_rows:
                c_dec = str(c_row["decision"]).upper()
                c_pid = str(c_row["placement_id"])
                concluded_pids.add(c_pid)
                if c_dec == "ACADEMIC_REVIEW_COMPLETE":
                    conclusions_dict["complete"] += 1
                    conclusions_dict["total"] += 1
                elif c_dec == "ACADEMIC_REVISION_REQUIRED":
                    conclusions_dict["revision_required"] += 1
                    conclusions_dict["total"] += 1

            # Pending conclusions: placements that are COMPLETED or ACTIVE but not yet concluded
            for p_row in placement_rows:
                pid = str(p_row["placement_id"])
                if pid not in concluded_pids:
                    conclusions_dict["pending"] += 1

            # Workplace Evaluations breakdown
            eval_approved = 0
            eval_changes = 0
            eval_rejected = 0

            for e_row in evaluation_rows:
                edec = str(e_row["decision"]).upper()
                cnt = int(e_row["cnt"] or 0)
                if edec == "APPROVED":
                    eval_approved += cnt
                elif edec == "CHANGES_REQUESTED":
                    eval_changes += cnt
                elif edec == "REJECTED":
                    eval_rejected += cnt

            total_evals = eval_approved + eval_changes + eval_rejected
            approved_rate = (
                round((eval_approved / total_evals) * 100.0, 1)
                if total_evals > 0
                else 100.0
            )

            # Program Performance list
            program_performance: list[dict[str, Any]] = []
            for prog, enrolled in sorted(prog_enrolled.items()):
                comp = prog_completed.get(prog, 0)
                act = prog_active.get(prog, 0)
                prog_comp_rate = round((comp / enrolled) * 100.0, 1) if enrolled > 0 else 0.0
                program_performance.append({
                    "program": prog,
                    "enrolled": enrolled,
                    "completed": comp,
                    "active": act,
                    "completion_rate": prog_comp_rate,
                })

            # -------------------------------------------------------------
            # Final Response Payload Formation (matching survey contract)
            # -------------------------------------------------------------
            return {
                "institution_id": str_inst_id,
                "institution_name": inst["name"],
                "registry_code": inst.get("registry_code"),
                "summary": {
                    "total_students": len(students_list),
                    "active_interns": active_count,
                    "completed_interns": completed_count,
                    "overall_attendance_rate": overall_attendance_rate,
                    "total_logged_hours": total_logged_hours,
                    "avg_weekly_hours_per_student": avg_weekly_hours_per_student,
                    "completion_rate": completion_rate,
                    "pending_teacher_reviews": pending_teacher_reviews_count,
                    "academic_conclusions_count": conclusions_dict["total"],
                },
                "attendance_metrics": {
                    "overall_rate": overall_attendance_rate,
                    "by_status_distribution": status_dist,
                    "by_day_type": day_type_counts,
                    "late_submissions_count": late_submissions_count,
                    "students": students_list,
                },
                "weekly_hours_monitoring": {
                    "current_week_hours": current_week_hours,
                    "avg_weekly_hours": avg_weekly_hours_per_student,
                    "weekly_trend": weekly_trend,
                    "by_program": by_program_list,
                    "by_organization": by_org_list,
                    "compliance_alerts": {
                        "overtime_students": len(overtime_candidates),
                        "zero_hours_this_week": zero_hours_this_week,
                    },
                },
                "internship_results": {
                    "total_placements": total_placements,
                    "by_status": status_counts,
                    "completion_rate": completion_rate,
                    "academic_conclusions": conclusions_dict,
                    "workplace_evaluations": {
                        "approved_rate": approved_rate,
                        "approved_count": eval_approved,
                        "changes_requested_count": eval_changes,
                        "rejected_count": eval_rejected,
                    },
                    "program_performance": program_performance,
                },
            }


university_analytics_service = UniversityAnalyticsService()

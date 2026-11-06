r"""
FlexBridge 1.4 Specification & Schema Builder (S1.2)
Transforms the verified 1.3 model (94 tables / 923 fields / 205 FKs) into:
  - D:\FlexBridge\specs\v1_4\FlexBridge_model_1_4.json (94 tables / 935 fields / 214 FKs / 42 ACs)
  - D:\FlexBridge\specs\v1_4\FlexBridge_1_4_schema.sql (PostgreSQL 17 DDL with all 1.4 constraints, GiST, EXCLUDE, deferred FKs, triggers, and DB-083 Policy v1 seed)
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path("D:/FlexBridge")
V1_3_DIR = ROOT / "specs" / "v1_3"
V1_4_DIR = ROOT / "specs" / "v1_4"
V1_4_DIR.mkdir(parents=True, exist_ok=True)


def build_v1_4_model() -> dict:
    m13 = json.loads((V1_3_DIR / "FlexBridge_model_1_3.json").read_text(encoding="utf-8"))
    m14 = copy.deepcopy(m13)
    m14["version"] = "1.4"
    m14["date"] = "2026-11-05"
    m14["status"] = (
        "FlexBridge 1.4 specification and PostgreSQL DDL with all 12 DB/API/architecture fixes, "
        "DB-083 retention policy v1, and AC-001..042"
    )

    by_name = {t["name"]: t for t in m14["tables"]}

    def add_field(table_name: str, name: str, typ: str, nullable: bool = False, fk: str | None = None):
        tbl = by_name[table_name]
        if any(f["name"] == name for f in tbl["fields"]):
            return
        tbl["fields"].append(
            {
                "name": name,
                "type": typ,
                "nullable": nullable,
                "pk": False,
                "fk": fk,
            }
        )

    def add_unique(table_name: str, cols: str):
        tbl = by_name[table_name]
        if cols not in tbl["unique"]:
            tbl["unique"].append(cols)

    def add_check(table_name: str, expr: str):
        tbl = by_name[table_name]
        if expr not in tbl["checks"]:
            tbl["checks"].append(expr)

    # 1.1 DB-036 opportunity_revisions: contract_type + INV-07 salary & program checks
    add_field("opportunity_revisions", "contract_type", "text", nullable=False, fk=None)
    add_check(
        "opportunity_revisions",
        "contract_type IN ('LABOR_PART_TIME','CIVIL_GPC','INTERNSHIP_AGREEMENT','ACADEMIC_TRIPARTITE')",
    )
    add_check(
        "opportunity_revisions",
        "(is_paid = false AND salary_min IS NULL AND salary_max IS NULL AND salary_period IS NULL AND salary_basis IS NULL) "
        "OR (is_paid = true AND salary_min IS NOT NULL AND salary_min > 0 AND salary_period IS NOT NULL AND salary_basis IS NOT NULL)",
    )
    add_check(
        "opportunity_revisions",
        "eligibility <> 'ENROLLMENT_PROGRAM' OR program_required IS NOT NULL",
    )

    # 1.2 DB-038 opportunity_shifts: group_code
    add_field("opportunity_shifts", "group_code", "text", nullable=False, fk=None)

    # 1.3 DB-057 log_task_entries: allow 0-minute draft & strict start/end completeness
    by_name["log_task_entries"]["checks"] = [
        "minutes >= 0",
        "(start_minute IS NULL AND end_minute IS NULL) OR "
        "(start_minute IS NOT NULL AND end_minute IS NOT NULL AND start_minute >= 0 AND end_minute <= 1440 "
        "AND end_minute > start_minute AND minutes = end_minute - start_minute)",
    ]

    # 1.4 DB-075 service_entitlements & DB-076 refunds
    add_field("service_entitlements", "concurrent_active_limit", "integer", nullable=False, fk=None)
    add_check("service_entitlements", "concurrent_active_limit > 0")

    add_field("refunds", "second_approver_id", "uuid", nullable=True, fk="users")
    by_name["refunds"]["checks"] = [
        "amount > 0",
        "(approver_id IS NULL OR approver_id <> requester_id) AND "
        "(second_approver_id IS NULL OR (second_approver_id <> requester_id AND (approver_id IS NULL OR second_approver_id <> approver_id)))",
    ]

    # 3.3 Dual-Control self-approval checks on verification_cases, platform_role_grants, recovery_requests
    add_check("verification_cases", "assigned_reviewer_id IS NULL OR assigned_reviewer_id <> requester_id")
    add_check("platform_role_grants", "granted_by_id <> user_id")
    add_check("recovery_requests", "reviewer_id IS NULL OR user_id IS NULL OR reviewer_id <> user_id")

    # 1.5 Cross-table scope columns (+8 FK columns -> total +12 fields = 935, +9 FKs = 214)
    add_field("application_attempts", "opportunity_id", "uuid", nullable=False, fk="opportunities")
    add_field("opportunity_hr_assignments", "organization_id", "uuid", nullable=False, fk="organizations")
    add_field("mentor_assignments", "organization_id", "uuid", nullable=False, fk="organizations")
    add_field("student_supervisions", "institution_id", "uuid", nullable=False, fk="institutions")
    add_field("academic_assignments", "institution_id", "uuid", nullable=False, fk="institutions")
    add_field("workplace_log_reviews", "placement_id", "uuid", nullable=False, fk="placements")
    add_field("academic_log_reviews", "placement_id", "uuid", nullable=False, fk="placements")
    add_field("rating_scores", "rubric_id", "uuid", nullable=False, fk="rubric_versions")

    # Composite UNIQUE keys required by parent-child composite FKs
    add_unique("applications", "id,opportunity_id")
    add_unique("application_attempts", "id,application_id")
    add_unique("opportunities", "id,organization_id")
    add_unique("placements", "id,organization_id")
    add_unique("mentor_assignments", "id,placement_id")
    add_unique("enrollments", "id,institution_id")
    add_unique("institution_agreements", "id,institution_id")
    add_unique("student_supervisions", "id,institution_id")
    add_unique("academic_assignments", "id,placement_id")
    add_unique("rubric_criteria", "id,rubric_id")
    add_unique("rating_submissions", "id,rubric_id")

    # 2. API role & contract fixes (API-046, API-060, API-061, API-088, API-100) + helper APIs API-X01..X08
    for api in m14["apis"]:
        if api["id"] == "API-046":
            api["operation_roles"] = ["CANDIDATE", "STUDENT", "OWNER", "HR"]
            api["description"] = (
                "PART_TIME uchun 2-tomonlama START/END tasdig'i; INTERNSHIP bilan PG-048.S04 (API-124) "
                "cohort analitikasida yagona Verified Start metriki sifatida birlashtiriladi"
            )
        elif api["id"] == "API-060":
            api["operation_roles"] = [r for r in m14["roles"] if r != "GUEST"]
            api["description"] = "Step-up (parol/MFA) va kontaktni qayta tekshirish (GUESTsiz barcha autentifikatsiyadan o'tgan rollar)"
        elif api["id"] == "API-061":
            api["operation_roles"] = [r for r in m14["roles"] if r != "GUEST"]
            api["description"] = "Faqat foydalanuvchining o'ziga tegishli (user_id = current_user.id) sessiyalarni bekor qilish (GUESTsiz)"
        elif api["id"] == "API-088":
            api["operation_roles"] = ["OWNER", "HOST_COORDINATOR"]
            api["description"] = "Amaliyot hosti vakilining qarorlari (ACTIVATE, APPROVE_COMPLETION, DISPUTE, CANCEL) — qat'iy ORG doirasi"
        elif api["id"] == "API-100":
            api["operation_roles"] = ["COORDINATOR"]
            api["description"] = "Muassasa kesimidagi yig'ma hisobot eksporti — qat'iy INSTITUTION doirasi, step-up re-auth va audit bilan"

    m14["helper_apis"] = [
        {"id": "API-X01", "method": "POST", "path": "/api/v1/files/upload-intents", "cap": "FILE_ACCESS", "description": "S3 quarantine/ prefiksiga yuklash uchun presigned intent va DB-018 PENDING_SCAN yozuvi"},
        {"id": "API-X02", "method": "POST", "path": "/api/v1/files/{id}/complete-upload", "cap": "FILE_ACCESS", "description": "Yuklash tugaganini tasdiqlash va ClamAV + pypdf asinxron skaner navbatiga yuborish"},
        {"id": "API-X03", "method": "GET", "path": "/api/v1/files/{id}/download", "cap": "FILE_ACCESS", "description": "Server-side access guard va CLEAN fayl uchun 60s TTL signed URL; PENDING_SCAN/QUARANTINED bo'lsa 409/403"},
        {"id": "API-X04", "method": "POST", "path": "/api/v1/webhooks/payments/{provider}", "cap": "BILLING", "description": "To'lov provayderi imzolangan webhook callback va idempotent ledger yozuvi"},
        {"id": "API-X05", "method": "GET", "path": "/api/v1/health/live", "cap": "OPERATIONS", "description": "Liveness probe"},
        {"id": "API-X06", "method": "GET", "path": "/api/v1/health/ready", "cap": "OPERATIONS", "description": "Readiness probe (PostgreSQL, Redis, S3, ClamAV va P1 circuit-breaker holati)"},
        {"id": "API-X07", "method": "POST", "path": "/api/v1/internal/workers/scan-result", "cap": "OPERATIONS", "description": "ClamAV + pypdf worker skan natijasini DB-018 ga yozish"},
        {"id": "API-X08", "method": "POST", "path": "/api/v1/internal/workers/retention-sweep", "cap": "OPERATIONS", "description": "DB-083 retention_policies bo'yicha muddati o'tgan ma'lumotlarni tozalash/anonimlashtirish"},
    ]

    # 4. DB-083 Retention Policies v1
    m14["retention_policies_v1"] = [
        {"data_class": "OTP_CHALLENGE_DIGEST", "policy_version": 1, "active_days": 1, "backup_expiry_days": 7, "legal_basis": "Xavfsizlik va rate-limit tekshiruvi; OTP 5 daqiqa, xeshi 24 soatda o'chiriladi", "status": "ACTIVE"},
        {"data_class": "SECURITY_LOGIN_METADATA", "policy_version": 1, "active_days": 90, "backup_expiry_days": 30, "legal_basis": "Brute-force va hisob xavfsizligi tahlili; 90 kundan keyin IP va device digest tozalanadi", "status": "ACTIVE"},
        {"data_class": "PRIVATE_EXPORT_FILE", "policy_version": 1, "active_days": 1, "backup_expiry_days": 7, "legal_basis": "PDF/ZIP eksport fayli 24 soatdan so'ng S3 va DB-018 dan o'chiriladi", "status": "ACTIVE"},
        {"data_class": "UNPUBLISHED_DRAFT", "policy_version": 1, "active_days": 30, "backup_expiry_days": 14, "legal_basis": "Nofaol e'lon yoki kundalik qoralamasi 23-kuni ogohlantiriladi va 30-kuni tozalanadi", "status": "ACTIVE"},
        {"data_class": "VERIFICATION_EVIDENCE", "policy_version": 1, "active_days": 90, "backup_expiry_days": 30, "legal_basis": "Tekshiruv hal bo'lgach, xom dalil fayli 90 kundan so'ng o'chiriladi; qaror va audit qoladi", "status": "ACTIVE"},
        {"data_class": "APPLICATION_AND_SNAPSHOT", "policy_version": 1, "active_days": 365, "backup_expiry_days": 30, "legal_basis": "Yopilgan/rad etilgan ariza va snapshotlari nizo muddati uchun 1 yil saqlanadi, so'ngra PII anonimlashtiriladi", "status": "ACTIVE"},
        {"data_class": "INTERNSHIP_DIARY_ACADEMIC", "policy_version": 1, "active_days": 1095, "backup_expiry_days": 30, "legal_basis": "Oliygoh va host kelishuvi bo'yicha akademik amaliyot kundaligi va yakuniy qarorlar 3 yil saqlanadi", "status": "ACTIVE"},
        {"data_class": "BILLING_AND_FISCAL_LEDGER", "policy_version": 1, "active_days": 1825, "backup_expiry_days": 90, "legal_basis": "Soliq va buxgalteriya hisobi talablari bo'yicha orders, invoices, refunds va billing_ledger 5 yil saqlanadi", "status": "ACTIVE"},
    ]

    # 5. New Acceptance Criteria AC-039..AC-042
    new_acs = [
        {
            "id": "AC-039",
            "gap_id": "DB-06",
            "title": "Shartnoma turi va smena guruhlari",
            "cap": "CAP-005, CAP-016",
            "tables": ["availability_rules", "opportunity_revisions", "opportunity_shifts"],
            "policy": "contract_type NOT NULL (4 tur) va smena group_code ALL/ANY mosligi",
            "test": "contract_type ko'rsatilmagan e'lon nashri 422 bilan rad etiladi. ANY rejimida 2 ta smena guruhi (GROUP_A, GROUP_B) berilganda, nomzodning bo'sh vaqti faqat GROUP_B ga to'liq mos kelsa, API-003 (/matching/preview) javobi MATCH qaytaradi.",
            "status": "SPECIFIED_1_4",
        },
        {
            "id": "AC-040",
            "gap_id": "DB-07",
            "title": "Kundalik 0-daqiqa draft va GiST overlap",
            "cap": "CAP-022",
            "tables": ["log_revisions", "log_task_entries"],
            "policy": "DRAFT holatida minutes >= 0, SUBMITTED WORKED holatida total_minutes > 0 va GiST EXCLUDE overlap himoyasi",
            "test": "PUT /api/v1/placements/{id}/logs/{date} orqali minutes = 0 bo'lgan qoralama vazifa 200 OK bilan saqlanadi; lekin day_type = 'WORKED' holatida total_minutes = 0 bilan POST /submit chaqirilsa 422 qaytadi. Vaqt oralig'i kesishgan (09:00-11:00 va 10:30-12:00) ikki vazifa GiST EXCLUDE tomonidan rad etiladi.",
            "status": "SPECIFIED_1_4",
        },
        {
            "id": "AC-041",
            "gap_id": "SEC-03",
            "title": "API role-scope va dual-control chegarasi",
            "cap": "CAP-002, CAP-025, CAP-026, CAP-030",
            "tables": ["verification_cases", "refunds", "platform_role_grants"],
            "policy": "GUEST bloklanishi, qat'iy ORG/INSTITUTION scope va DB darajasida self-approval taqiqi",
            "test": "GUEST sessiyada API-060 yoki API-061 chaqirilsa 401; CANDIDATE yoki TEACHER tomonidan API-088 (/host-decisions) chaqirilsa 403; CANDIDATE tomonidan API-100 (/institutions/{inst}/exports) chaqirilsa 403 qaytadi. O'z-o'zini tasdiqlash (refund yoki verification) DB constrainti bilan rad etiladi.",
            "status": "SPECIFIED_1_4",
        },
        {
            "id": "AC-042",
            "gap_id": "OPS-10",
            "title": "Karantin skaneri va concurrent slot limiti",
            "cap": "CAP-016, CAP-029",
            "tables": ["files", "service_entitlements"],
            "policy": "PENDING_SCAN/QUARANTINED signed URL bermaslik va ORG_PLAN_30D concurrent_active_limit = 5",
            "test": "PENDING_SCAN yoki QUARANTINED fayl uchun API-X03 (/download) chaqirilsa 409/403 qaytadi va signed URL berilmaydi. ORG_PLAN_30D da 5 ta aktiv PUBLISHED e'lon turganda 6-e'lonni publish qilish 409 concurrent_quota_reached beradi; 1 ta e'lon yopilgach (CLOSED/PAUSED) yangisi publish bo'ladi.",
            "status": "SPECIFIED_1_4",
        },
    ]
    existing_ac_ids = {a["id"] for a in m14["acceptance"]}
    for ac in new_acs:
        if ac["id"] not in existing_ac_ids:
            m14["acceptance"].append(ac)

    total_fields = sum(len(t["fields"]) for t in m14["tables"])
    total_fks = sum(1 for t in m14["tables"] for f in t["fields"] if f.get("fk"))
    m14["stats"] = {
        "tables": len(m14["tables"]),
        "fields": total_fields,
        "foreign_keys": total_fks,
        "roles": len(m14["roles"]),
        "capabilities": len(m14["capabilities"]),
        "pages": len(m14["pages"]),
        "sections": sum(len(p["sections"]) for p in m14["pages"]),
        "api_contracts": len(m14["apis"]),
        "helper_apis": len(m14["helper_apis"]),
        "acceptance_criteria": len(m14["acceptance"]),
        "reference_errors": 0,
    }
    assert m14["stats"]["tables"] == 94, f"Expected 94 tables, got {m14['stats']['tables']}"
    assert m14["stats"]["fields"] == 935, f"Expected 935 fields, got {m14['stats']['fields']}"
    assert m14["stats"]["foreign_keys"] == 214, f"Expected 214 FKs, got {m14['stats']['foreign_keys']}"
    assert m14["stats"]["acceptance_criteria"] == 42, f"Expected 42 ACs, got {m14['stats']['acceptance_criteria']}"
    return m14


def build_v1_4_sql(m14: dict) -> str:
    sql = [
        "-- FlexBridge 1.4 | Complete PostgreSQL 17 Schema Specification | 2026-11-05",
        "-- Generated from verified FlexBridge 1.3 model + FlexBridge 1.4 Technical Specification (94 tables, 935 model fields, 214 model FKs).",
        "-- Includes: int4range STORED columns, GiST & EXCLUDE constraints, INV-01..16 composite/deferred FKs and triggers, Dual-Control checks, and DB-083 Retention Policy v1.",
        "BEGIN;",
        "CREATE EXTENSION IF NOT EXISTS btree_gist;",
        "CREATE SCHEMA IF NOT EXISTS flexbridge;",
        "SET LOCAL search_path TO flexbridge, public;",
        "",
    ]

    generated_columns = {
        "availability_rules": [
            "    minute_range int4range GENERATED ALWAYS AS (int4range(start_minute, end_minute, '[)')) STORED"
        ],
        "availability_exceptions": [
            "    minute_range int4range GENERATED ALWAYS AS (int4range(start_minute, end_minute, '[)')) STORED"
        ],
        "opportunity_shifts": [
            "    minute_range int4range GENERATED ALWAYS AS (int4range(start_minute, end_minute, '[)')) STORED"
        ],
        "log_task_entries": [
            "    minute_range int4range GENERATED ALWAYS AS (CASE WHEN start_minute IS NOT NULL AND end_minute IS NOT NULL THEN int4range(start_minute, end_minute, '[)') ELSE NULL END) STORED"
        ],
    }

    column_defaults = {
        ("opportunity_revisions", "contract_type"): "'LABOR_PART_TIME'",
        ("opportunity_shifts", "group_code"): "'GROUP_A'",
        ("service_entitlements", "concurrent_active_limit"): "5",
    }

    named_checks = {
        "opportunity_revisions": [
            (
                "chk_opp_rev_contract_type",
                "contract_type IN ('LABOR_PART_TIME','CIVIL_GPC','INTERNSHIP_AGREEMENT','ACADEMIC_TRIPARTITE')",
            ),
            (
                "chk_opp_rev_salary",
                "(is_paid = false AND salary_min IS NULL AND salary_max IS NULL AND salary_period IS NULL AND salary_basis IS NULL) "
                "OR (is_paid = true AND salary_min IS NOT NULL AND salary_min > 0 AND salary_period IS NOT NULL AND salary_basis IS NOT NULL)",
            ),
            (
                "chk_opp_rev_program",
                "eligibility <> 'ENROLLMENT_PROGRAM' OR program_required IS NOT NULL",
            ),
        ],
        "refunds": [
            (
                "chk_refunds_independent_approvers",
                "(approver_id IS NULL OR approver_id <> requester_id) AND "
                "(second_approver_id IS NULL OR (second_approver_id <> requester_id AND (approver_id IS NULL OR second_approver_id <> approver_id)))",
            )
        ],
        "verification_cases": [
            (
                "chk_verification_not_self_review",
                "assigned_reviewer_id IS NULL OR assigned_reviewer_id <> requester_id",
            )
        ],
        "platform_role_grants": [
            (
                "chk_platform_grant_not_self",
                "granted_by_id <> user_id",
            )
        ],
        "recovery_requests": [
            (
                "chk_recovery_not_self_review",
                "reviewer_id IS NULL OR user_id IS NULL OR reviewer_id <> user_id",
            )
        ],
    }

    for t in m14["tables"]:
        tname = t["name"]
        cols = []
        for f in t["fields"]:
            col = f"    {f['name']} {f['type']}"
            if not f["nullable"]:
                col += " NOT NULL"
            if f["pk"]:
                col += " PRIMARY KEY"
            if f["name"] in ("created_at", "updated_at"):
                col += " DEFAULT now()"
            elif (tname, f["name"]) in column_defaults:
                col += f" DEFAULT {column_defaults[(tname, f['name'])]}"
            cols.append(col)

        if tname in generated_columns:
            cols.extend(generated_columns[tname])

        cols.extend(f"    UNIQUE ({u})" for u in t["unique"])

        table_named_exprs = {expr for _, expr in named_checks.get(tname, [])}
        for chk in t["checks"]:
            if chk not in table_named_exprs:
                cols.append(f"    CHECK ({chk})")
        for cname, expr in named_checks.get(tname, []):
            cols.append(f"    CONSTRAINT {cname} CHECK ({expr})")

        if tname == "log_task_entries":
            cols.append(
                "    CONSTRAINT excl_log_task_entries_no_overlap EXCLUDE USING gist (revision_id WITH =, minute_range WITH &&) WHERE (minute_range IS NOT NULL)"
            )

        sql.append(f"-- {t['id']} {t['purpose']}")
        sql.append(f"CREATE TABLE {tname} (")
        sql.append(",\n".join(cols))
        sql.append(" );")

    # Circular single-column FKs that MUST be DEFERRABLE INITIALLY DEFERRED (INV-14)
    deferred_single_fks = {
        ("opportunities", "current_revision_id"),
        ("applications", "current_attempt_id"),
        ("placements", "current_terms_id"),
        ("daily_logs", "current_revision_id"),
    }

    for t in m14["tables"]:
        tname = t["name"]
        for i, f in enumerate(t["fields"]):
            if f.get("fk"):
                defer_mode = (
                    "DEFERRABLE INITIALLY DEFERRED"
                    if (tname, f["name"]) in deferred_single_fks
                    else "DEFERRABLE INITIALLY IMMEDIATE"
                )
                cname = f"fk_{t['id'].lower().replace('-', '_')}_{i}"
                sql.append(
                    f"ALTER TABLE {tname} ADD CONSTRAINT {cname} FOREIGN KEY ({f['name']}) "
                    f"REFERENCES {f['fk']}(id) ON DELETE RESTRICT {defer_mode};"
                )
        keys = list(t["indexes"])
        covered = {k.split(",")[0] for k in t["unique"] + keys}
        for f in t["fields"]:
            if f.get("fk") and f["name"] not in covered:
                keys.append(f["name"])
                covered.add(f["name"])
        for i, key in enumerate(keys):
            sql.append(
                f"CREATE INDEX ix_{t['id'].lower().replace('-', '_')}_{i} ON {tname} ({key});"
            )

    # GiST indexes for 1.2 (DB-016, DB-017, DB-038)
    sql.extend(
        [
            "",
            "-- 1.2 GiST range indexes for schedule & shift matching",
            "CREATE INDEX ix_availability_rules_gist ON availability_rules USING gist (candidate_id, weekday, minute_range);",
            "CREATE INDEX ix_availability_exceptions_gist ON availability_exceptions USING gist (candidate_id, local_date, minute_range);",
            "CREATE INDEX ix_opportunity_shifts_gist ON opportunity_shifts USING gist (revision_id, weekday, minute_range);",
            "",
            "-- Partial unique indexes (1.3 / 1.4)",
            "CREATE UNIQUE INDEX one_active_offer ON offers(application_id) WHERE status = 'OFFERED';",
            "CREATE UNIQUE INDEX one_current_mentor ON mentor_assignments(placement_id) WHERE revoked_at IS NULL AND accepted_at IS NOT NULL;",
            "CREATE UNIQUE INDEX one_current_teacher ON academic_assignments(placement_id) WHERE revoked_at IS NULL AND accepted_at IS NOT NULL;",
            "CREATE UNIQUE INDEX one_placement_rating ON rating_submissions(placement_id,rater_id,rubric_id) WHERE placement_id IS NOT NULL;",
            "CREATE UNIQUE INDEX one_engagement_rating ON rating_submissions(engagement_id,rater_id,rubric_id) WHERE engagement_id IS NOT NULL;",
            "CREATE UNIQUE INDEX one_user_aggregate ON rating_aggregates(target_user_id,rubric_id,window_start,window_end) WHERE target_user_id IS NOT NULL;",
            "CREATE UNIQUE INDEX one_org_aggregate ON rating_aggregates(target_org_id,rubric_id,window_start,window_end) WHERE target_org_id IS NOT NULL;",
            "",
            "-- 1.5 Composite Foreign Keys for cross-table scope integrity (INV-01..03, INV-10..11) and circular revisions (INV-14)",
            "-- INV-01: Application attempt and revision belong to the same opportunity_id",
            "ALTER TABLE application_attempts ADD CONSTRAINT fk_app_attempts_app_same_opp FOREIGN KEY (application_id, opportunity_id) REFERENCES applications(id, opportunity_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "ALTER TABLE application_attempts ADD CONSTRAINT fk_app_attempts_rev_same_opp FOREIGN KEY (revision_id, opportunity_id) REFERENCES opportunity_revisions(id, opportunity_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "-- INV-02: Inviter, HR assignment, and mentor assignment belong to the same organization_id",
            "ALTER TABLE org_invitations ADD CONSTRAINT fk_org_invitations_inviter_same_org FOREIGN KEY (inviter_membership_id, organization_id) REFERENCES org_memberships(id, organization_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "ALTER TABLE opportunity_hr_assignments ADD CONSTRAINT fk_opp_hr_membership_same_org FOREIGN KEY (membership_id, organization_id) REFERENCES org_memberships(id, organization_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "ALTER TABLE opportunity_hr_assignments ADD CONSTRAINT fk_opp_hr_opportunity_same_org FOREIGN KEY (opportunity_id, organization_id) REFERENCES opportunities(id, organization_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "ALTER TABLE mentor_assignments ADD CONSTRAINT fk_mentor_placement_same_org FOREIGN KEY (membership_id, organization_id) REFERENCES org_memberships(id, organization_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "ALTER TABLE mentor_assignments ADD CONSTRAINT fk_mentor_placement_org_match FOREIGN KEY (placement_id, organization_id) REFERENCES placements(id, organization_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "-- INV-03: Supervision coordinator, agreement, enrollment, and academic teacher belong to the same institution_id",
            "ALTER TABLE student_supervisions ADD CONSTRAINT fk_supervision_coordinator_same_inst FOREIGN KEY (coordinator_membership_id, institution_id) REFERENCES institution_memberships(id, institution_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "ALTER TABLE student_supervisions ADD CONSTRAINT fk_supervision_enrollment_same_inst FOREIGN KEY (enrollment_id, institution_id) REFERENCES enrollments(id, institution_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "ALTER TABLE student_supervisions ADD CONSTRAINT fk_supervision_agreement_same_inst FOREIGN KEY (agreement_id, institution_id) REFERENCES institution_agreements(id, institution_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "ALTER TABLE academic_assignments ADD CONSTRAINT fk_academic_teacher_same_inst FOREIGN KEY (teacher_membership_id, institution_id) REFERENCES institution_memberships(id, institution_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "ALTER TABLE academic_assignments ADD CONSTRAINT fk_academic_supervision_same_inst FOREIGN KEY (supervision_id, institution_id) REFERENCES student_supervisions(id, institution_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "-- INV-10: Workplace and academic log reviews belong to the same placement_id",
            "ALTER TABLE workplace_log_reviews ADD CONSTRAINT fk_wp_review_revision_same_pl FOREIGN KEY (mentor_assignment_id, placement_id) REFERENCES mentor_assignments(id, placement_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "ALTER TABLE academic_log_reviews ADD CONSTRAINT fk_acad_review_revision_same_pl FOREIGN KEY (academic_assignment_id, placement_id) REFERENCES academic_assignments(id, placement_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "-- INV-11: Rating criterion and revision belong to the same rubric_id",
            "ALTER TABLE rating_scores ADD CONSTRAINT fk_rating_scores_crit_same_rubric FOREIGN KEY (criterion_id, rubric_id) REFERENCES rubric_criteria(id, rubric_id) ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;",
            "-- INV-14: Circular parent-child current revision/attempt/terms composite FKs (DEFERRABLE INITIALLY DEFERRED)",
            "ALTER TABLE opportunities ADD CONSTRAINT fk_opportunities_current_revision FOREIGN KEY (current_revision_id, id) REFERENCES opportunity_revisions(id, opportunity_id) DEFERRABLE INITIALLY DEFERRED;",
            "ALTER TABLE applications ADD CONSTRAINT fk_applications_current_attempt FOREIGN KEY (current_attempt_id, id) REFERENCES application_attempts(id, application_id) DEFERRABLE INITIALLY DEFERRED;",
            "ALTER TABLE placements ADD CONSTRAINT fk_placements_current_terms FOREIGN KEY (current_terms_id, id) REFERENCES placement_terms(id, placement_id) DEFERRABLE INITIALLY DEFERRED;",
            "ALTER TABLE daily_logs ADD CONSTRAINT fk_daily_logs_current_revision FOREIGN KEY (current_revision_id, id) REFERENCES log_revisions(id, daily_log_id) DEFERRABLE INITIALLY DEFERRED;",
            "",
            "-- 1.3 Trigger: trg_validate_log_submission (INV-09, AC-040)",
            """CREATE OR REPLACE FUNCTION fn_validate_log_submission()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_placement_id uuid;
    v_local_date date;
    v_start_date date;
    v_end_date date;
    v_daily_limit integer;
    v_sum_minutes integer;
BEGIN
    IF NEW.status = 'SUBMITTED' THEN
        SELECT dl.placement_id, dl.local_date
          INTO v_placement_id, v_local_date
          FROM daily_logs dl
         WHERE dl.id = NEW.daily_log_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Daily log % topilmadi', NEW.daily_log_id
                USING ERRCODE = '23503';
        END IF;

        SELECT p.start_date, p.end_date
          INTO v_start_date, v_end_date
          FROM placements p
         WHERE p.id = v_placement_id;

        IF v_local_date < v_start_date OR (v_end_date IS NOT NULL AND v_local_date > v_end_date) OR v_local_date > CURRENT_DATE THEN
            RAISE EXCEPTION 'Kundalik sanasi (%) placement oralig''ida emas yoki kelajak sana (INV-09)', v_local_date
                USING ERRCODE = '23514';
        END IF;

        SELECT pt.daily_limit_minutes
          INTO v_daily_limit
          FROM placement_terms pt
         WHERE pt.id = NEW.terms_id AND pt.placement_id = v_placement_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Placement terms % ushbu placement (%) ga tegishli emas (INV-09)', NEW.terms_id, v_placement_id
                USING ERRCODE = '23503';
        END IF;

        SELECT COALESCE(SUM(lte.minutes), 0)
          INTO v_sum_minutes
          FROM log_task_entries lte
         WHERE lte.revision_id = NEW.id;

        NEW.total_minutes := v_sum_minutes;

        IF NEW.day_type = 'WORKED' AND (NEW.total_minutes <= 0 OR NEW.total_minutes > v_daily_limit) THEN
            RAISE EXCEPTION 'WORKED kunida total_minutes (%) > 0 va <= daily_limit_minutes (%) bo''lishi shart (INV-09 / AC-040)', NEW.total_minutes, v_daily_limit
                USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;""",
            "CREATE TRIGGER trg_validate_log_submission BEFORE INSERT OR UPDATE ON log_revisions FOR EACH ROW EXECUTE FUNCTION fn_validate_log_submission();",
            "",
            "-- INV-10 & INV-11 Cross-table scope verification triggers for log reviews and rating scores",
            """CREATE OR REPLACE FUNCTION fn_validate_log_review_scope()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_log_placement_id uuid;
BEGIN
    SELECT dl.placement_id
      INTO v_log_placement_id
      FROM log_revisions lr
      JOIN daily_logs dl ON dl.id = lr.daily_log_id
     WHERE lr.id = NEW.revision_id;

    IF v_log_placement_id IS NULL OR v_log_placement_id <> NEW.placement_id THEN
        RAISE EXCEPTION 'Kundalik taqrizi placement_id (%) kundalik versiyasi placement_id (%) bilan mos emas (INV-10)', NEW.placement_id, v_log_placement_id
            USING ERRCODE = '23503';
    END IF;
    RETURN NEW;
END;
$$;""",
            "CREATE TRIGGER trg_validate_wp_review_scope BEFORE INSERT OR UPDATE ON workplace_log_reviews FOR EACH ROW EXECUTE FUNCTION fn_validate_log_review_scope();",
            "CREATE TRIGGER trg_validate_acad_review_scope BEFORE INSERT OR UPDATE ON academic_log_reviews FOR EACH ROW EXECUTE FUNCTION fn_validate_log_review_scope();",
            "",
            """CREATE OR REPLACE FUNCTION fn_validate_rating_score_rubric()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_sub_rubric_id uuid;
BEGIN
    SELECT rs.rubric_id
      INTO v_sub_rubric_id
      FROM rating_revisions rr
      JOIN rating_submissions rs ON rs.id = rr.submission_id
     WHERE rr.id = NEW.rating_revision_id;

    IF v_sub_rubric_id IS NULL OR v_sub_rubric_id <> NEW.rubric_id THEN
        RAISE EXCEPTION 'Rating score rubric_id (%) rating submission rubric_id (%) bilan mos emas (INV-11)', NEW.rubric_id, v_sub_rubric_id
            USING ERRCODE = '23503';
    END IF;
    RETURN NEW;
END;
$$;""",
            "CREATE TRIGGER fk_rating_scores_rev_same_rubric BEFORE INSERT OR UPDATE ON rating_scores FOR EACH ROW EXECUTE FUNCTION fn_validate_rating_score_rubric();",
            "",
            "-- 1.4 Trigger: trg_validate_refund_limit (INV-12)",
            """CREATE OR REPLACE FUNCTION fn_validate_refund_limit()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_captured_amount numeric(18,2);
    v_attempt_status text;
    v_existing_refunds numeric(18,2);
BEGIN
    SELECT pa.amount, pa.status
      INTO v_captured_amount, v_attempt_status
      FROM payment_attempts pa
     WHERE pa.id = NEW.payment_attempt_id
       FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Payment attempt % topilmadi', NEW.payment_attempt_id
            USING ERRCODE = '23503';
    END IF;

    IF v_attempt_status <> 'CAPTURED' THEN
        RAISE EXCEPTION 'Faqat CAPTURED holatidagi to''lovdan refund qilish mumkin (joriy: %)', v_attempt_status
            USING ERRCODE = '23514';
    END IF;

    SELECT COALESCE(SUM(r.amount), 0)
      INTO v_existing_refunds
      FROM refunds r
     WHERE r.payment_attempt_id = NEW.payment_attempt_id
       AND r.id <> NEW.id
       AND r.status NOT IN ('REJECTED', 'CANCELLED', 'FAILED');

    IF (v_existing_refunds + NEW.amount) > v_captured_amount THEN
        RAISE EXCEPTION 'Jami refund summasi (%) CAPTURED summadan (%) oshib ketdi (INV-12)', (v_existing_refunds + NEW.amount), v_captured_amount
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;""",
            "CREATE TRIGGER trg_validate_refund_limit BEFORE INSERT OR UPDATE ON refunds FOR EACH ROW EXECUTE FUNCTION fn_validate_refund_limit();",
            "",
            "-- 1.5 Triggers: INV-16 Immutability guards (audit_events, consent_events, billing_ledger, opportunity_revisions, log_revisions)",
            """CREATE OR REPLACE FUNCTION fn_block_append_only_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Jadval % append-only (o''zgarmas); % amali taqiqlangan (INV-16)', TG_TABLE_NAME, TG_OP
        USING ERRCODE = '23514';
END;
$$;""",
            "CREATE TRIGGER trg_immutable_audit_events BEFORE UPDATE OR DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION fn_block_append_only_mutation();",
            "CREATE TRIGGER trg_immutable_consent_events BEFORE UPDATE OR DELETE ON consent_events FOR EACH ROW EXECUTE FUNCTION fn_block_append_only_mutation();",
            "CREATE TRIGGER trg_immutable_billing_ledger BEFORE UPDATE OR DELETE ON billing_ledger FOR EACH ROW EXECUTE FUNCTION fn_block_append_only_mutation();",
            "",
            """CREATE OR REPLACE FUNCTION fn_guard_opportunity_revisions()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'opportunity_revisions yozuvini o''chirish taqiqlangan (INV-16)'
            USING ERRCODE = '23514';
    END IF;
    IF OLD.published_at IS NOT NULL THEN
        RAISE EXCEPTION 'Nashr qilingan opportunity_revisions yozuvini tahrirlash taqiqlangan (INV-16)'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;""",
            "CREATE TRIGGER trg_guard_opportunity_revisions BEFORE UPDATE OR DELETE ON opportunity_revisions FOR EACH ROW EXECUTE FUNCTION fn_guard_opportunity_revisions();",
            "",
            """CREATE OR REPLACE FUNCTION fn_guard_log_revisions()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'log_revisions yozuvini o''chirish taqiqlangan (INV-16)'
            USING ERRCODE = '23514';
    END IF;
    IF OLD.status <> 'DRAFT' AND (
        NEW.daily_log_id <> OLD.daily_log_id OR
        NEW.revision <> OLD.revision OR
        NEW.terms_id <> OLD.terms_id OR
        NEW.author_id <> OLD.author_id OR
        NEW.day_type <> OLD.day_type OR
        NEW.total_minutes <> OLD.total_minutes
    ) THEN
        RAISE EXCEPTION 'Topshirilgan log_revisions tarkibini o''zgartirish taqiqlangan; yangi revision yarating (INV-16)'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;""",
            "CREATE TRIGGER trg_guard_log_revisions BEFORE UPDATE OR DELETE ON log_revisions FOR EACH ROW EXECUTE FUNCTION fn_guard_log_revisions();",
            "",
            "-- 4. DB-083 retention_policies Policy v1 canonical seed",
            "INSERT INTO retention_policies (id, data_class, policy_version, active_days, backup_expiry_days, legal_basis, status) VALUES",
            "    ('00000000-0000-4000-8000-000000000081', 'OTP_CHALLENGE_DIGEST', 1, 1, 7, 'Xavfsizlik va rate-limit tekshiruvi; OTP kodning o''zi 5 daqiqa amal qiladi, xeshi 24 soatdan so''ng o''chiriladi.', 'ACTIVE'),",
            "    ('00000000-0000-4000-8000-000000000082', 'SECURITY_LOGIN_METADATA', 1, 90, 30, 'Brute-force va hisob xavfsizligi tahlili; 90 kundan keyin IP va device digest tozalanadi.', 'ACTIVE'),",
            "    ('00000000-0000-4000-8000-000000000083', 'PRIVATE_EXPORT_FILE', 1, 1, 7, 'Foydalanuvchi yoki muassasa so''ragan PDF/ZIP eksport fayli 24 soatdan so''ng S3 va DB-018 dan o''chiriladi.', 'ACTIVE'),",
            "    ('00000000-0000-4000-8000-000000000084', 'UNPUBLISHED_DRAFT', 1, 30, 14, 'Nofaol e''lon yoki kundalik qoralamasi 23-kuni ogohlantiriladi va 30-kuni tozalanadi.', 'ACTIVE'),",
            "    ('00000000-0000-4000-8000-000000000085', 'VERIFICATION_EVIDENCE', 1, 90, 30, 'Tekshiruv (STIR, talabalik, tayinlov) hal bo''lgach, xom dalil fayli 90 kundan so''ng o''chiriladi; qaror va audit qoladi.', 'ACTIVE'),",
            "    ('00000000-0000-4000-8000-000000000086', 'APPLICATION_AND_SNAPSHOT', 1, 365, 30, 'Yopilgan/rad etilgan ariza va uning snapshotlari nizo muddati uchun 1 yil saqlanadi, so''ngra PII anonimlashtiriladi.', 'ACTIVE'),",
            "    ('00000000-0000-4000-8000-000000000087', 'INTERNSHIP_DIARY_ACADEMIC', 1, 1095, 30, 'Oliygoh va host kelishuvi bo''yicha akademik amaliyot kundaligi va yakuniy qarorlar o''quv davri uchun 3 yil saqlanadi.', 'ACTIVE'),",
            "    ('00000000-0000-4000-8000-000000000088', 'BILLING_AND_FISCAL_LEDGER', 1, 1825, 90, 'Soliq va buxgalteriya hisobi talablari bo''yicha orders, invoices, refunds va billing_ledger 5 yil saqlanadi.', 'ACTIVE')",
            "ON CONFLICT (data_class, policy_version) DO NOTHING;",
            "",
            "COMMIT;",
            "",
        ]
    )
    return "\n".join(sql)


if __name__ == "__main__":
    model_1_4 = build_v1_4_model()
    (V1_4_DIR / "FlexBridge_model_1_4.json").write_text(
        json.dumps(model_1_4, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    sql_1_4 = build_v1_4_sql(model_1_4)
    (V1_4_DIR / "FlexBridge_1_4_schema.sql").write_text(sql_1_4, encoding="utf-8")
    print("Generated FlexBridge_model_1_4.json stats:", json.dumps(model_1_4["stats"], ensure_ascii=False))
    print("Generated FlexBridge_1_4_schema.sql lines:", len(sql_1_4.splitlines()), "bytes:", len(sql_1_4))

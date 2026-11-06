"""Schema loader, metadata inspector, and PostgreSQL 1.4 invariant verifier (S2.1.1)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from app.core.config import settings

RETENTION_POLICIES_V1: tuple[dict[str, Any], ...] = (
    {
        "id": "00000000-0000-4000-8000-000000000081",
        "data_class": "OTP_CHALLENGE_DIGEST",
        "policy_version": 1,
        "active_days": 1,
        "backup_expiry_days": 7,
        "legal_basis": "Xavfsizlik va rate-limit tekshiruvi; OTP kodning o'zi 5 daqiqa amal qiladi, xeshi 24 soatdan so'ng o'chiriladi.",
        "status": "ACTIVE",
    },
    {
        "id": "00000000-0000-4000-8000-000000000082",
        "data_class": "SECURITY_LOGIN_METADATA",
        "policy_version": 1,
        "active_days": 90,
        "backup_expiry_days": 30,
        "legal_basis": "Brute-force va hisob xavfsizligi tahlili; 90 kundan keyin IP va device digest tozalanadi.",
        "status": "ACTIVE",
    },
    {
        "id": "00000000-0000-4000-8000-000000000083",
        "data_class": "PRIVATE_EXPORT_FILE",
        "policy_version": 1,
        "active_days": 1,
        "backup_expiry_days": 7,
        "legal_basis": "Foydalanuvchi yoki muassasa so'ragan PDF/ZIP eksport fayli 24 soatdan so'ng S3 va DB-018 dan o'chiriladi.",
        "status": "ACTIVE",
    },
    {
        "id": "00000000-0000-4000-8000-000000000084",
        "data_class": "UNPUBLISHED_DRAFT",
        "policy_version": 1,
        "active_days": 30,
        "backup_expiry_days": 14,
        "legal_basis": "Nofaol e'lon yoki kundalik qoralamasi 23-kuni ogohlantiriladi va 30-kuni tozalanadi.",
        "status": "ACTIVE",
    },
    {
        "id": "00000000-0000-4000-8000-000000000085",
        "data_class": "VERIFICATION_EVIDENCE",
        "policy_version": 1,
        "active_days": 90,
        "backup_expiry_days": 30,
        "legal_basis": "Tekshiruv (STIR, talabalik, tayinlov) hal bo'lgach, xom dalil fayli 90 kundan so'ng o'chiriladi; qaror va audit qoladi.",
        "status": "ACTIVE",
    },
    {
        "id": "00000000-0000-4000-8000-000000000086",
        "data_class": "APPLICATION_AND_SNAPSHOT",
        "policy_version": 1,
        "active_days": 365,
        "backup_expiry_days": 30,
        "legal_basis": "Yopilgan/rad etilgan ariza va uning snapshotlari nizo muddati uchun 1 yil saqlanadi, so'ngra PII anonimlashtiriladi.",
        "status": "ACTIVE",
    },
    {
        "id": "00000000-0000-4000-8000-000000000087",
        "data_class": "INTERNSHIP_DIARY_ACADEMIC",
        "policy_version": 1,
        "active_days": 1095,
        "backup_expiry_days": 30,
        "legal_basis": "Oliygoh va host kelishuvi bo'yicha akademik amaliyot kundaligi va yakuniy qarorlar o'quv davri uchun 3 yil saqlanadi.",
        "status": "ACTIVE",
    },
    {
        "id": "00000000-0000-4000-8000-000000000088",
        "data_class": "BILLING_AND_FISCAL_LEDGER",
        "policy_version": 1,
        "active_days": 1825,
        "backup_expiry_days": 90,
        "legal_basis": "Soliq va buxgalteriya hisobi talablari bo'yicha orders, invoices, refunds va billing_ledger 5 yil saqlanadi.",
        "status": "ACTIVE",
    },
)

RETENTION_POLICY_V1_CODES: tuple[str, ...] = tuple(
    item["data_class"] for item in RETENTION_POLICIES_V1
)


def load_model_1_4(path: Path | None = None) -> dict[str, Any]:
    """Load the canonical `FlexBridge_model_1_4.json` specification."""
    target = path or settings.model_json_path
    with target.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_schema_sql(path: Path | None = None) -> str:
    """Read the canonical `FlexBridge_1_4_schema.sql` DDL script."""
    target = path or settings.schema_sql_path
    return target.read_text(encoding="utf-8")


def get_schema_summary() -> dict[str, Any]:
    """Return verified structural counts and invariant summary for FlexBridge 1.4."""
    model = load_model_1_4()
    sql_text = load_schema_sql()
    report = load_verification_report()
    counts = model["stats"]
    return {
        "schema_version": model.get("version", "1.4"),
        "schema_sql_exists": settings.schema_sql_path.exists(),
        "schema_sql_bytes": len(sql_text.encode("utf-8")),
        "counts": counts,
        "retention_policy_v1_count": len(RETENTION_POLICIES_V1),
        "postgres_verification": {
            "all_checks_passed": report.get("all_checks_passed", False),
            "passed_checks": report.get("passed_checks", 0),
            "total_checks": report.get("total_checks", 0),
            "engine": report.get("engine", "unknown"),
        },
    }


def get_retention_policies_v1() -> list[dict[str, Any]]:
    """Return the 8 legal retention policies defined in 1.4 PDF section 6 (`DB-083`)."""
    return [dict(item) for item in RETENTION_POLICIES_V1]


def load_verification_report(path: Path | None = None) -> dict[str, Any]:
    """Load the PostgreSQL 1.4 invariant verification report JSON."""
    target = path or settings.verification_report_path
    if not target.exists():
        return {"all_checks_passed": False, "passed_checks": 0, "total_checks": 0}
    with target.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def run_live_postgres_verification() -> dict[str, Any]:
    """Execute `verify_v1_4_schema.mjs` against PGlite/PostgreSQL (`btree_gist`) and return the report."""
    completed = subprocess.run(
        ["node", str(settings.verifier_script_path)],
        cwd=str(settings.verifier_script_path.parent.parent.parent),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)

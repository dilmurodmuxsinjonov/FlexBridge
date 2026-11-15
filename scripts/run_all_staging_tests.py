#!/usr/bin/env python3
"""Run all staging verification test suites sequentially and summarize results."""

import os
import subprocess
import sys
import time
from pathlib import Path
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def reset_rate_limits():
    """Reset rate limit buckets between regression runs to avoid false positives."""
    try:
        values = dotenv_values(Path(REPO_ROOT) / "infra" / ".env")
        password = values.get("POSTGRES_PASSWORD")
        if not password:
            return
        url = URL.create(
            "postgresql+psycopg",
            username=values.get("POSTGRES_USER") or "flexbridge_owner",
            password=password,
            host="127.0.0.1",
            port=5432,
            database=values.get("POSTGRES_DB") or "flexbridge",
        )
        engine = create_engine(url, poolclass=NullPool, connect_args={"prepare_threshold": None})
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE flexbridge.auth_rate_limits"))
    except Exception:
        pass

TEST_SCRIPTS = [
    "scripts/test_bff_staging.py",
    "scripts/test_candidate_applications_staging.py",
    "scripts/test_candidate_internship_logs_staging.py",
    "scripts/test_candidate_offers_engagements_staging.py",
    "scripts/test_candidate_profile_staging.py",
    "scripts/test_candidate_ratings_appeals_staging.py",
    "scripts/test_employer_billing_staging.py",
    "scripts/test_employer_kanban_staging.py",
    "scripts/test_employer_mentor_staging.py",
    "scripts/test_employer_organization_staging.py",
    "scripts/test_operator_finance_staging.py",
    "scripts/test_operator_portal_staging.py",
    "scripts/test_operator_support_ops_staging.py",
    "scripts/test_opportunity_application_staging.py",
    "scripts/test_university_academic_reviews_staging.py",
    "scripts/test_university_exports_staging.py",
    "scripts/test_university_placements_staging.py",
    "scripts/test_user_support_privacy_staging.py",
    "scripts/test_vacancy_lifecycle_interviews_staging.py",
    "scripts/test_candidate_saved_notifications_staging.py",
    "scripts/test_candidate_enrollments_exceptions_staging.py",
    "scripts/test_user_security_sessions_staging.py",
    "scripts/test_public_cms_footer_staging.py",
    "scripts/test_standalone_auth_pages_staging.py",
    "scripts/test_candidate_portfolio_certificates_staging.py",
    "scripts/test_employer_search_staging.py",
    "scripts/test_university_analytics_staging.py",
    "scripts/test_telegram_phone_verification_staging.py",
    "scripts/test_full_resume_org_univ_directory_staging.py",
    "scripts/test_university_timetable_staging.py",
]

def main():
    print("=" * 80)
    print("  FLEXBRIDGE 1.4: COMPREHENSIVE MULTI-SUITE REGRESSION RUNNER")
    print(f"  Total test suites to run: {len(TEST_SCRIPTS)}")
    print("=" * 80)

    results = []
    start_total = time.time()

    for i, script in enumerate(TEST_SCRIPTS, 1):
        print(f"\n[{i}/{len(TEST_SCRIPTS)}] Running {script}...")
        reset_rate_limits()
        start_suite = time.time()
        res = subprocess.run([sys.executable, script], capture_output=True, text=True)
        duration = round(time.time() - start_suite, 2)
        passed = (res.returncode == 0)
        results.append((script, passed, duration, res.stdout, res.stderr))
        if passed:
            print(f"  ✓ PASSED in {duration}s")
        else:
            print(f"  ✗ FAILED in {duration}s (exit {res.returncode})")
            print("  --- STDOUT ---")
            print(res.stdout[-500:] if len(res.stdout) > 500 else res.stdout)
            print("  --- STDERR ---")
            print(res.stderr[-500:] if len(res.stderr) > 500 else res.stderr)

    total_duration = round(time.time() - start_total, 2)
    print("\n" + "=" * 80)
    print(f"  REGRESSION RUN SUMMARY (Total Time: {total_duration}s)")
    print("=" * 80)

    all_passed = True
    for script, passed, dur, _, _ in results:
        status_str = "PASSED" if passed else "FAILED"
        print(f"  [{status_str:6}] {dur:5.2f}s - {script}")
        if not passed:
            all_passed = False

    print("=" * 80)
    if all_passed:
        print(f"  SUCCESS: ALL {len(TEST_SCRIPTS)} TEST SUITES PASSED 100% GREEN!")
        sys.exit(0)
    else:
        print("  FAILURE: ONE OR MORE SUITES FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()

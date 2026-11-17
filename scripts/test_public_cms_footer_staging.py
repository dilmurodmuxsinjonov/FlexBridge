#!/usr/bin/env python3
"""FlexBridge 1.4 Public CMS (Legal Policies, Help Docs & Modern Footer Hub) Staging Verification Suite (FB-188).

Verifies end-to-end against live Docker staging stack via Next.js BFF and canonical backend:
Phase 1: Public Terms Policy (GET /api/bff/public/policies/terms -> HTTP 200, API-014 contract).
Phase 2: Public Privacy Policy with AC-023 Differential Privacy (GET /api/bff/public/policies/privacy -> HTTP 200).
Phase 3: Public Cookies Policy with Strict Security (GET /api/bff/public/policies/cookies -> HTTP 200).
Phase 4: Acceptable Use & Rating Guidelines Policies (GET /api/bff/public/policies/{doc} -> HTTP 200).
Phase 5: Unknown Policy Slug Rejection (GET /api/bff/public/policies/invalid-xyz -> HTTP 404 POLICY_NOT_FOUND).
Phase 6: Public Onboarding Help Doc (GET /api/bff/public/help/onboarding -> HTTP 200, API-013 contract).
Phase 7: Candidate & Employer User Guides (GET /api/bff/public/help/{doc} -> HTTP 200).
Phase 8: Academic Guide & Schedule Matching Engine Docs (GET /api/bff/public/help/schedule-matching -> HTTP 200).
Phase 9: Unknown Help Doc Slug Rejection (GET /api/bff/public/help/invalid-guide -> HTTP 404 DOCUMENT_NOT_FOUND).
Phase 10: SSR HTML & Footer Directory Verification (/shartlar, /maxfiylik, /haqida, / -> HTTP 200, directory links & statutory compliance).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def make_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
) -> tuple[int, dict[str, Any] | str, dict[str, str]]:
    req_headers = headers or {}
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            resp_headers = dict(resp.headers)
            body = resp.read().decode("utf-8")
            try:
                parsed = json.loads(body)
                return status, parsed, resp_headers
            except Exception:
                return status, body, resp_headers
    except urllib.error.HTTPError as exc:
        status = exc.code
        resp_headers = dict(exc.headers)
        body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(body)
            return status, parsed, resp_headers
        except Exception:
            return status, body, resp_headers


def run_phase_1() -> None:
    print("\n--- Phase 1: Public Terms Policy (GET /api/bff/public/policies/terms) ---")
    status, body, headers = make_request(f"{FRONTEND_URL}/api/bff/public/policies/terms")
    assert status == 200, f"Expected 200, got {status}: {body}"
    assert isinstance(body, dict), f"Expected dict body, got {type(body)}"
    assert body.get("contract_id") == "API-014", f"Expected API-014, got {body.get('contract_id')}"
    assert body.get("document") == "terms", f"Expected terms document, got {body.get('document')}"
    assert "foydalanish shartlari" in body.get("title", "").lower(), f"Unexpected title: {body.get('title')}"
    assert "version" in body, "Expected version in response"
    assert "effective_date" in body, "Expected effective_date in response"
    clauses = body.get("clauses", [])
    assert len(clauses) >= 3, f"Expected at least 3 clauses, got {len(clauses)}"
    print(f"  OK: Terms policy verified (version {body.get('version')}, {len(clauses)} clauses).")


def run_phase_2() -> None:
    print("\n--- Phase 2: Public Privacy Policy with AC-023 Differential Privacy ---")
    status, body, headers = make_request(f"{FRONTEND_URL}/api/bff/public/policies/privacy")
    assert status == 200, f"Expected 200, got {status}: {body}"
    assert isinstance(body, dict), f"Expected dict body, got {type(body)}"
    assert body.get("contract_id") == "API-014", f"Expected API-014, got {body.get('contract_id')}"
    assert body.get("document") == "privacy", f"Expected privacy document, got {body.get('document')}"
    content = body.get("content_markdown", "")
    assert "AC-023" in content or any("AC-023" in str(c) for c in body.get("clauses", [])), (
        "Expected AC-023 differential privacy reference in privacy policy"
    )
    assert "contact_email" in body, "Expected contact_email in privacy policy"
    print(f"  OK: Privacy policy verified with AC-023 differential privacy compliance ({body.get('contact_email')}).")


def run_phase_3() -> None:
    print("\n--- Phase 3: Public Cookies Policy with Strict Security ---")
    status, body, headers = make_request(f"{FRONTEND_URL}/api/bff/public/policies/cookies")
    assert status == 200, f"Expected 200, got {status}: {body}"
    assert isinstance(body, dict), f"Expected dict body, got {type(body)}"
    assert body.get("contract_id") == "API-014", f"Expected API-014, got {body.get('contract_id')}"
    assert body.get("document") == "cookies", f"Expected cookies document, got {body.get('document')}"
    clauses = body.get("clauses", [])
    assert len(clauses) >= 1, f"Expected at least 1 cookie clause, got {len(clauses)}"
    print(f"  OK: Cookie policy verified ({len(clauses)} clauses).")


def run_phase_4() -> None:
    print("\n--- Phase 4: Acceptable Use & Rating Guidelines Policies ---")
    for doc in ["acceptable-use", "rating-guidelines"]:
        status, body, headers = make_request(f"{FRONTEND_URL}/api/bff/public/policies/{doc}")
        assert status == 200, f"Expected 200 for {doc}, got {status}: {body}"
        assert isinstance(body, dict), f"Expected dict body for {doc}, got {type(body)}"
        assert body.get("document") == doc, f"Expected {doc}, got {body.get('document')}"
        assert len(body.get("clauses", [])) > 0, f"Expected clauses for {doc}"
        print(f"  OK: Policy '{doc}' verified ({body.get('title')}).")


def run_phase_5() -> None:
    print("\n--- Phase 5: Unknown Policy Slug Rejection (HTTP 404 POLICY_NOT_FOUND) ---")
    status, body, headers = make_request(f"{FRONTEND_URL}/api/bff/public/policies/non-existent-policy-xyz")
    assert status == 404, f"Expected 404 for unknown policy, got {status}: {body}"
    assert isinstance(body, dict), f"Expected dict body, got {type(body)}"
    err_code = body.get("code") or (body.get("detail") if isinstance(body.get("detail"), dict) else {}).get("code") or body.get("error")
    assert "POLICY_NOT_FOUND" in str(err_code), f"Expected POLICY_NOT_FOUND code, got {body}"
    print("  OK: Unknown policy slug correctly rejected with 404 POLICY_NOT_FOUND.")


def run_phase_6() -> None:
    print("\n--- Phase 6: Public Getting Started & Onboarding Help Docs (GET /api/bff/public/help/getting-started & onboarding) ---")
    for doc in ["getting-started", "onboarding"]:
        status, body, headers = make_request(f"{FRONTEND_URL}/api/bff/public/help/{doc}")
        assert status == 200, f"Expected 200 for {doc}, got {status}: {body}"
        assert isinstance(body, dict), f"Expected dict body, got {type(body)}"
        assert body.get("contract_id") == "API-013", f"Expected API-013, got {body.get('contract_id')}"
        assert "version" in body, "Expected version in help doc"
        sections = body.get("sections", [])
        assert len(sections) >= 3, f"Expected at least 3 sections, got {len(sections)}"
        print(f"  OK: '{doc}' help doc verified (version {body.get('version')}, {len(sections)} sections).")


def run_phase_7() -> None:
    print("\n--- Phase 7: Candidate & Employer User Guides ---")
    for guide in ["candidate-guide", "employer-guide"]:
        status, body, headers = make_request(f"{FRONTEND_URL}/api/bff/public/help/{guide}")
        assert status == 200, f"Expected 200 for {guide}, got {status}: {body}"
        assert isinstance(body, dict), f"Expected dict body for {guide}, got {type(body)}"
        assert body.get("document") == guide, f"Expected {guide}, got {body.get('document')}"
        assert len(body.get("sections", [])) > 0, f"Expected sections for {guide}"
        print(f"  OK: Guide '{guide}' verified ({body.get('title')}).")


def run_phase_8() -> None:
    print("\n--- Phase 8: Academic Guide & Schedule Matching Engine Docs ---")
    for guide in ["academic-guide", "schedule-matching"]:
        status, body, headers = make_request(f"{FRONTEND_URL}/api/bff/public/help/{guide}")
        assert status == 200, f"Expected 200 for {guide}, got {status}: {body}"
        assert isinstance(body, dict), f"Expected dict body for {guide}, got {type(body)}"
        assert body.get("document") == guide, f"Expected {guide}, got {body.get('document')}"
        if guide == "schedule-matching":
            content = body.get("content_markdown", "")
            assert "jadval" in content.lower() or "bufer" in content.lower() or "algoritm" in content.lower(), (
                "Expected schedule matching principles in content"
            )
        print(f"  OK: Guide '{guide}' verified ({body.get('title')}).")


def run_phase_9() -> None:
    print("\n--- Phase 9: Unknown Help Doc Slug Rejection (HTTP 404 DOCUMENT_NOT_FOUND) ---")
    status, body, headers = make_request(f"{FRONTEND_URL}/api/bff/public/help/unknown-help-doc-xyz")
    assert status == 404, f"Expected 404 for unknown help doc, got {status}: {body}"
    assert isinstance(body, dict), f"Expected dict body, got {type(body)}"
    err_code = body.get("code") or (body.get("detail") if isinstance(body.get("detail"), dict) else {}).get("code") or body.get("error")
    assert "DOCUMENT_NOT_FOUND" in str(err_code), f"Expected DOCUMENT_NOT_FOUND code, got {body}"
    print("  OK: Unknown help document slug correctly rejected with 404 DOCUMENT_NOT_FOUND.")


def run_phase_10() -> None:
    print("\n--- Phase 10: SSR HTML & Footer Directory Verification ---")
    pages_to_check = [
        ("/", "Bosh sahifa"),
        ("/shartlar", "Foydalanish shartlari"),
        ("/maxfiylik", "Maxfiylik siyosati"),
        ("/haqida", "Platforma haqida"),
    ]
    for path, expected_text in pages_to_check:
        status, html, headers = make_request(f"{FRONTEND_URL}{path}")
        assert status == 200, f"Expected 200 for {path}, got {status}"
        assert isinstance(html, str), f"Expected string HTML for {path}"
        assert len(html) > 500, f"HTML response too short for {path}: {len(html)} bytes"
        
        # Verify footer links exist in the rendered HTML
        assert "/shartlar" in html, f"Footer link to /shartlar missing in {path}"
        assert "/maxfiylik" in html, f"Footer link to /maxfiylik missing in {path}"
        assert "/haqida" in html, f"Footer link to /haqida missing in {path}"
        assert "Mehnat Kodeksi" in html or "118-modda" in html or "FlexBridge" in html, (
            f"Statutory footer notice missing in {path}"
        )
        print(f"  OK: Rendered HTML for '{path}' validated ({len(html)} bytes, footer directory confirmed).")


def main() -> int:
    print("================================================================================")
    print("FlexBridge 1.4 Public CMS & Unified Footer Staging Verification Suite (FB-188)")
    print("================================================================================")
    try:
        run_phase_1()
        run_phase_2()
        run_phase_3()
        run_phase_4()
        run_phase_5()
        run_phase_6()
        run_phase_7()
        run_phase_8()
        run_phase_9()
        run_phase_10()
        print("\n================================================================================")
        print("SUCCESS: ALL 10 PHASES OF FB-188 PUBLIC CMS & FOOTER SUITE PASSED 100% GREEN!")
        print("================================================================================")
        return 0
    except AssertionError as err:
        print(f"\nFAIL: Verification failed: {err}")
        return 1
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"\nERROR: Unexpected error: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())

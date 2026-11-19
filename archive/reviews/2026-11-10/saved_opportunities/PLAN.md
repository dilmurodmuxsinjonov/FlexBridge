# Saved Opportunities Implementation Plan (API-004, API-037, API-038)

## 1. Context & Scope
- **Domain**: Candidate Opportunities (`JOB` domain)
- **Capability**: `CAP-006` (`SAVE_JOB`)
- **Contracts**:
  - `API-004`: `POST /api/v1/saved-opportunities` (Toggle idempotent, candidate's own candidate profile only)
  - `API-037`: `GET /api/v1/me/saved-opportunities` (List candidate's saved opportunities; closed/archived opportunity status preserved)
  - `API-038`: `DELETE /api/v1/me/saved-opportunities/{id}` (Candidate's own row only; idempotent repeat 204)
- **Primary Table**: `DB-040` (`saved_opportunities`: `id`, `created_at`, `updated_at`, `candidate_id`, `opportunity_id`, unique `(candidate_id, opportunity_id)`)
- **Referenced Tables**:
  - `DB-035` (`opportunities`: `id`, `kind`, `status`, `closed_at`, `current_revision_id`, `organization_id`)
  - `DB-036` (`opportunity_revisions`: `id`, `title`, `work_mode`, `contract_type`, `is_paid`)
  - `DB-012` (`candidate_profiles`: `id`, `user_id`)
  - `DB-006` (`audit_events`)

---

## 2. Technical Architecture & Constraints
1. **Governance & Actor Authority**:
   - `account_authority(conn, actor)` ensures caller has an active user account and non-revoked session.
   - `candidate_id_for(actor)` retrieves the calling user's candidate profile. If none exists, raises HTTP 403 `CANDIDATE_PROFILE_REQUIRED`.
   - If an explicit `candidate_id` is supplied in the request body, `owns_candidate(actor.user_id, candidate_id)` enforces strict ownership. Cross-candidate spoofing raises HTTP 403 `CANDIDATE_ACCESS_DENIED`.

2. **API-004 POST /api/v1/saved-opportunities**:
   - Input: `{"opportunity_id": UUID, "candidate_id": Optional[UUID], "toggle": Optional[bool]}`
   - Opportunity existence: Verified against `flexbridge.opportunities`. If not found, raises HTTP 404 `OPPORTUNITY_NOT_FOUND`.
   - Idempotency & Toggle:
     - Check existing row for `(candidate_id, opportunity_id)`.
     - If `toggle=True` and row exists: delete row, record audit event, return `{"saved": False, "opportunity_id": ..., "id": None}` with status 200.
     - If `toggle=True` and row does not exist: insert row, record audit event, return `{"saved": True, "opportunity_id": ..., "id": ...}` with status 201.
     - If `toggle=False` (default):
       - If row exists: return existing row `{"saved": True, "opportunity_id": ..., "id": ...}` with status 200.
       - If row does not exist: insert row, record audit event, return `{"saved": True, "opportunity_id": ..., "id": ...}` with status 201.

3. **API-037 GET /api/v1/me/saved-opportunities**:
   - Scope: Only returns saved opportunities for `candidate_id_for(actor)`.
   - Single SQL join: `saved_opportunities` JOIN `opportunities` LEFT JOIN `opportunity_revisions`.
   - Status preservation: preserves `status` (`PUBLISHED`, `CLOSED`, `ARCHIVED`, `DRAFT`) and provides `is_closed` boolean indicator.
   - Pagination: `page` (default 1) and `page_size` (default 20, max 100), ordered by `saved_opportunities.created_at.desc()`.

4. **API-038 DELETE /api/v1/me/saved-opportunities/{id}**:
   - Accepts either `saved_opportunities.id` or `opportunity_id` as `{id}` for maximum client flexibility.
   - Ownership isolation:
     - If row exists for another candidate: strictly raise HTTP 403 `SAVED_OPPORTUNITY_ACCESS_DENIED`.
     - If row exists for this candidate: delete row, record audit event, return HTTP 204 No Content.
     - If row does not exist: return HTTP 204 No Content (idempotent `repeat204`).

---

## 3. Test & Verification Plan
- `backend/tests/security/test_saved_opportunities_api004_037_038.py`:
  1. Candidate can save opportunity (API-004) -> 201 Created.
  2. Candidate repeat save is idempotent -> 200 OK without duplication.
  3. Toggle mode: toggling existing save deletes it -> 200 OK (`saved=False`).
  4. Candidate can list saved opportunities (API-037) -> returns items with opportunity details.
  5. Closed opportunity retains status and `is_closed=True` in saved list.
  6. Candidate can unsave opportunity by ID (API-038) -> 204 No Content.
  7. Repeat unsave is idempotent -> 204 No Content.
  8. Unsave by opportunity_id directly -> 204 No Content.
- `backend/tests/security/test_saved_opportunities_adversarial.py`:
  1. Unauthenticated request -> 401.
  2. Non-candidate user -> 403 `CANDIDATE_PROFILE_REQUIRED`.
  3. Candidate attempting to save for another candidate -> 403 `CANDIDATE_ACCESS_DENIED`.
  4. Candidate attempting to delete another candidate's saved opportunity -> 403 `SAVED_OPPORTUNITY_ACCESS_DENIED`.
  5. Saving non-existent opportunity ID -> 404 `OPPORTUNITY_NOT_FOUND`.
  6. Audit trail verification: `opportunity_saved` and `opportunity_unsaved` events logged in `audit_events`.

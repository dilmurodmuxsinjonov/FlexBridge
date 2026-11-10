## API-108 (read-only) review report

Reviewed paths:
- backend/alembic/versions/0018_academic_decisions.py
- backend/app/db/academic_decisions.py
- backend/app/services/academic_decisions.py
- backend/app/api/v1/academic_decisions.py
- backend/app/db/storage.py
- backend/app/main.py
- backend/ACADEMIC_DECISIONS.md

### Findings
- None identified as material P1/P2 defects against the explicit bundle contract.

Reasoning:
- DDL enforces PUBLIC vs LEGACY_IMPORT proof separation, basis digest integrity, and one-public-proof-per-assignment/terms/basis behavior.
- Service logic checks current teacher authority, exact consent, current plan/version, stale digest, and idempotent replay before creating a new conclusion.
- DB-side guards enforce same-transaction audit stamping and reject forged/missing/stale proof while preserving legacy DB-054 rows and unrelated host flows.
- DTO validation rejects non-official grade/credit/signature inputs.

Uncertainty note: this is a read-only static review; no test commands were run.


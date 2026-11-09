# Issue59 implementation decisions, after actual planning review

PR58 source was accepted at757 passing tests twice; its evidence-head CI must pass
before merge and this source change. Keep this package separate after that merge.
The current file API/service signature still has the confirmed authority gap.

The isolated b251644 expanded probe initially failed15 tests22.77s:12 actual
security-denial assertions and3 invalid self-grant fixture writes. The existing
chk_platform_grant_not_self correctly rejected those3. A distinct trusted grantor
was added to the fixture; no runtime guard changed. The corrected expanded15 all
failed19.27s with201/202/200 responses, proving the stale-authority gap across
initiate/complete/download for logout, expiry, auth version, suspension and late
sensitive role. These are not15 anonymous attack paths. Original probe1 overlaps.

Wait evidence is deliberately precise: completion waits on its actual file row;
the old download plain SELECT is held by an actual ACCESS EXCLUSIVE file-table lock;
initiation has no old business row, so it uses a service-entry barrier after real
HTTP middleware/dependency authentication. Only completion/download claim physical
SQL waits observed through holder PID pg_blocking_pids. Fixtures are trusted SQL
state/role mutations and storage HEAD/presign doubles, never actual S3/AV proof.

Implementation:

1. Pass actual ActorContext into the3 owner service methods/callers. No legacy
   owner_id/requester_id/user-id-only compatibility authorization. The exact owner
   check remains, current forged-other-session and valid PASSWORD controls required.
2. Extract existing account_authority unchanged from institution_onboarding into
   authority.py and reimport it into onboarding, so existing tests/monkeypatch aliases
   remain. It performs current user/session and existing SENSITIVE_ROLES assurance
   from actual roles_for, not cached actor roles. No new privilege/MFA policy.
3. Initiation has no existing file business lock: enter transaction, account guard,
   then presign and insert, holding authority through commit. Completion locks owned
   file, account guard before HEAD, state/length/version checks, update/enqueue, commit.
   Download locks owned file, account guard, clean/reference checks, presign, commit.
   Preserve previous state/ownership semantics; no sign/head before final authority.
4. Recheck after database waits; authorization is evaluated at the guarded boundary.
   Row locks serialize revocations/security mutations but do not freeze expiry time
   through arbitrary provider delay. Do not claim a clock freeze or an impossible
   instantaneous atomic transaction across PostgreSQL/provider.
5. Keep scanning an authenticated recorded upload after the owner later logs out.
   The asynchronous worker is a trusted system actor, not a fake user session. Add
   actual MinIO proof of logout then scanCLEAN, old token owner-download401, preserving
   source/version/fencing and no arbitrary anonymous worker endpoint.
6. Controls staged in test_files_authority_controls.py: reverse real logout waits
   on guard-held PID for all3 methods, valid current ordinary PASSWORD, fake session
   rejection, and provider rollback. Add current-sensitive MFA/ordinary teacher
   compatibility where it exercises the shared extracted helper. Existing EDU race/
   privacy and actual storage integration must pass; no test-only session bypass.
7. Candidate/CV sibling authority is still separate; attaching new CV provenance
   in57 did not close its actor-id-only boundary. Do not expand silently or claim it
   fixed. Record a later scoped audit after59. Source/code/peer/full CI evidence and
   Antigravity/project journals stay current. Pilotfalse, placeholders remain.


Evidence note: expanded_corrected_probe.py.txt is reconstructed from the preserved
initial probe plus the recorded independent-grantor-only fixture correction; no
historical byte hash is claimed. The later root test additionally counts HEAD
calls and accepts an optional supplied owner for positive MFA controls. Both
pre-fix denial assertions and actual execution XML remain preserved separately.

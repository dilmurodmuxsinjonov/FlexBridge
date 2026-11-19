I’ll inspect only the named repository files and the focused fixture diff context, then give a
narrow, read-only review without running tests or commands.

A. Candidate/CV fixture: The negative test retains its security assertion: PENDING_SCAN, SCANNING,
and QUARANTINED files must return 409, and the candidate’s CV link must remain unset. The fixture
now supplies the quarantine VersionId and ETag while setting object_version to the ETag; CLEAN
remains version-bound. I see no concrete regression in this delta.

B. Issue59 findings and recommendations:

 1. The final-authority gap remains in the current files flow. The routes resolve an ActorContext,
but pass only its user ID to the three owner operations—upload initiation, upload completion, and
signed download. The service has no transaction-bound check of the current session or current
account roles. The reported logout-while-waiting behavior is consistent with that gap: middleware
authentication can become stale before the request acquires its file-row lock.
 2. Pass the actual ActorContext through all three routes and service methods; do not add a
user-ID-only fallback. Within each service transaction, recheck current account/session authority
and the global sensitive-role MFA requirement. Ordinary PASSWORD sessions should remain valid for
non-sensitive accounts; determine sensitive roles from current database state, not cached actor
roles.
 3. Order checks around business and storage work. For completion, lock and validate the owned file
row, then check authority before HEAD, and hold the authority locks through HEAD, the file update,
outbox enqueue, and commit. For download, lock and validate the file row, check authority, then sign
while the locks remain held through commit. For initiation, check authority before presigning or
inserting the intent. This gives the logout race a clear ordering: if logout commits before the
guarded check, reject without mutation; if the request obtains authority locks first, logout waits
for its commit. session_authority uses user-then-session locking, matching logout’s
user-then-session order.
 4. Prefer a narrow shared-helper extraction. Move onboarding’s existing account_authority logic
into services/authority.py and have onboarding and the file service use it. Keep this scoped: don’t
broadly refactor institution-role authority or include the candidate/CV sibling methods in Issue59.
 5. Preserve file and worker semantics. Keep owner checks, state transitions, HEAD size validation,
stored VersionId/ETag, object_version behavior, source/version fencing, retry and deduplication
behavior, and transactional outbox enqueue unchanged. The trusted asynchronous scan should continue
using its recorded intent independently of a later owner logout.

Prioritized regression coverage: First, test the blocked completion/logout race and the reverse
ordering, asserting both response and row/outbox state. Also cover final session expiry/revocation
and a sensitive role present at the guarded check; verify rollback leaves no partial file or event;
and retain valid PASSWORD-owner initiation/completion/download cases plus existing version-bound
storage assertions. Candidate/CV caller coverage is a separate scope.

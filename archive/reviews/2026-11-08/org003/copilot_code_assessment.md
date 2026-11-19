# Disposition of the pinned ownership code review

GitHub Copilot CLI completed exit0 using only view/glob/grep in the detached
0953ebd04ad73a87f3389a0040f25a389012bdfe worktree. Writes, shell, built-in MCPs and
remote export were disabled. Its model was not independently reported. It found no
HTTP authorization bypass in the reviewed scope; this is a limited review, not a certificate.

1. **SQL reviewer proof boundary.** The deferred guard now also checks an active reviewer
   account and current platform MODERATOR grant. Actual opaque-bearer/MFA authentication
   belongs to the API, which locks the live user/session/grant rows through commit after
   business locks. SQL validates relational event/case/grant metadata. Direct database
   writers are trusted and can otherwise write grant tables; the event trigger does not
   authenticate an HTTP caller or claim to resist a privileged database compromise.
2. **Contact HMAC boundary.** The service computes and compares the purpose-bound binding
   under a contact row lock; the DTO accepts only the target's contact UUID. SQL checks
   contact identity, owner, verification timestamp and revocation, without possessing the
   application HMAC key. It does not independently verify an arbitrary direct-SQL digest.
   This application-trusted-DB invariant is explicit in OWNER_ADDITIONS.md. Changed-contact,
   revocation, stale consent and account-security tests cover the actual API boundary.
3. **Confirmed HTTP-reachable history issue: fixed.** Fresh invitation acceptance used to
   clear the old grant's revoked_at. It now selects only an active grant, checks the latest
   historical revocation and creates a new grant when needed. The old row remains exactly
   unchanged. A real invite -> accept -> membership revoke -> fresh invite -> accept
   regression verifies distinct IDs, one active grant and preserved old metadata. The
   invitation history query has a matching partial index after full uniqueness is replaced.

The complete affected suite before the last history-index-only change passed118 tests.
The final migration/invitation follow-up and committed complete CI are recorded separately;
initial flow, security and transaction results are supporting evidence, not an unchanged
final full-suite claim. Synthetic role/contact/CLEAN-file fixtures do not certify legal
identity, live delivery, production provisioning or browser acceptance.

# Issue59 - owner file transaction authority

Confirmed on pinned afd343ab749a1a2131172e662769ff8fb2369d2c in the separate clean
review worktree plus this isolated probe. Actual HTTP logout200 occurred after the
pending completion request was observed waiting on its real file-row holder PID.
Completion then returned202/SCANNING and queued1 event. Native1 failed33.57s.
The storage HEAD/presign is an explicit synthetic boundary, not actual S3/AV data.
No anonymous access, foreign ownership, completed scan or live deployment is claimed.

Implementation must follow PR58 acceptance/merge in a fresh branch. Root Codex owns
app/api/files.py, services/files_quarantine.py and file authority tests/docs. Review
planning before editing. Pass actual ActorContext through3 methods/callers and
recheck existing current-session/account/sensitive-role assurance at the guarded
boundary after business locks. No sessionless fallback. Preserve stored versions,
owner-only scope, existing ordinary PASSWORD behavior, outbox fencing and rollback.
Candidate/CV ordinary self-service callers remain a separately explicit audit scope.

This is not a failure of version binding and is not part of PR58's passing coverage.
Pilot remains false. Current PR58 reviews/CI do not close this security residual.

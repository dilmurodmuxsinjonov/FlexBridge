The proposed change is narrowly scoped: record_moderation_action has one production caller,
create_moderation_action_endpoint. Keep that endpoint’s require_platform(actor, 'MODERATOR') as the
early preflight, pass actor=actor, and change the service to accept ActorContext. Inside its
transaction, acquire the opportunity lock, then call moderator_authority(conn, actor) before reading
the revision or making the decision. Remove the service’s synthetic ActorContext(actor_id, '', ())
preflight, and use actor.user_id for the self-author check and all case, action, and audit writes.

The lock order fits the existing pattern: the opportunity business lock precedes authority checks;
moderator_authority then checks and locks user, session, and platform grant/role rows. The authority
module documents business-lock-before-guard, and appeal decisions use the same ordering. I found no
concrete lock-order or transaction regression in this scope. The planned concurrency tests should
use independent connections and exercise the actual session/MFA/grant rows so they prove both denial
after a completed change and serialization when authority is already locked.

One boundary to keep clear: row locks serialize database changes, but cannot stop expires_at from
passing after the post-lock authority check. The fix addresses grants that expire while the decision
waits for the opportunity lock; expiry during the remaining transaction is an existing time-based
authorization boundary, not a new regression from this change.

No files were changed, and I did not run tests or verify a SHA.


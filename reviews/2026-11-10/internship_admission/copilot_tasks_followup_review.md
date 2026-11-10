The correction closes the reported direct-SQL history gap; I found no concrete P1/P2 issue in this
delta.

The task-insert trigger now locks the placement and permits inserts only for its current terms while
the placement is PLANNED or PENDING_START_CONFIRMATION; it rejects terms that already have consent
or a PLAN_PUBLISHED event. That covers both superseded terms and previously published current terms,
including the initial-plan case that lacked consent and publication evidence.

In publish_plan, the current-terms projection is updated before task insertion, so the new guard
accepts the new plan’s tasks. The projection, tasks, and later publication event remain in the same
transaction: task or event failure rolls the projection and new terms back together. The projection
update is permitted by the migration’s placement guard in these statuses and retains the existing
single version increment. The service already holds the placement lock; the trigger’s lock is on
that same row, so I found no new lock-order issue.

The requested lifecycle test attempts inserts against both the initial terms and the published
terms. I did not run it or certify its result. I read the recorded launch-time hashes as context but
did not independently verify them. The stated academic/TEACHER admission, completion,
retry-receipt, pagination, and candidate-notification work remains unfinished; this is not an
acceptance or pilot claim.


# AGY011 capability smoke disposition

Actual SUCCESS/exit0/requested GeminiArgonHigh, reported model absent,
conversationb4a82985-f5a4-4861-8b3b-d29524b53980,99.81s. Agent reports actual
read-only command attempts under --mode auto --sandbox: git/gh user-profile
config denied, Copilot wrapper falsely exited0 while node was not found,
OpenCode config initialization failed, PostgreSQL loopback WSAEACCES10013.
These are failed capabilities, not completed review/native integration tests.

The dispatched task's final Python command had an accidental trailing plus.
Original dispatch was preserved and source task corrected; its report gives a
real socket denial rather than syntax error. AGY012 retries all five corrected
commands in ordinary CLI auto mode without the optional sandbox. No bypass flag,
login/token/config edits, installs or business mutations are authorized.

Master runner's optional --sandbox was removed because the required existing
GitHub/native/worker tooling is inaccessible in that sandbox. --mode auto remains;
no --dangerously-skip-permissions flag was added. The read-only smoke must establish
actual capabilities; it will not prove a future push/merge receives approval.
Main freeze and integration-only verification are unchanged.

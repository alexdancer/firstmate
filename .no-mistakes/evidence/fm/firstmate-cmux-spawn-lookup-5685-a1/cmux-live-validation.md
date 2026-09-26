# Focused cmux live validation

Socket preflight: PONG using the installed cmux CLI with a subprocess-local PATH prefix. Shared cmux settings were not changed.

Reproduced failures:
- Original live script stopped before launch because its generated brief left FIRSTMATE_SPEC unresolved.
- After filling the brief and using Pi's per-run approval for the isolated fixture, real Pi processed the brief and wrote the expected report. The live test then exited 1 because its single post-close probe raced asynchronous cmux removal. The lab remained intact.

Fixes: populate both brief placeholders; poll for typed exact-workspace absence for up to ten probes after successful close, preserving refusal if no proof arrives. Extend the existing direct-close regression with a pending removal response and enforce its return status.

Results:
1. PASS, live: real Pi scout launched, produced its generation-bound agent-start state, published its record, processed the brief, and wrote the expected report. Corrected live script exited 0 after confirmed cleanup.
2. PASS, live: new workspace created in a different existing window was absent from the current-window title projection, yet exact workspace/surface readiness, send and capture succeeded. This tests actual missing projection, not a simulated delayed-list response; a temporal listing delay was not manufactured.
3. PASS, live backend with injected submission error: refusing the staged send left no worker metadata, retained the real Treehouse copy and recovery record, and confirmed exact closure. A separate actual Pi trust-dialog run also refused unconfirmed processing.
4. PASS, live: replacing a real surface made the old pair refuse send, key, capture and kill. Closing the workspace and creating a same-title replacement never redirected stale operations. Replacement stayed live until its own guarded cleanup.
5. PASS, real cmux/Treehouse/Pi with injected failures: staged-launch mv failure, metadata mv failure and both tasks-axi start failures all retained copies and exact recovery, removed ordinary metadata and recorded closure=confirmed. Publication and dispatch observed genuine pi-ext agent-start before publication. No fake lifecycle event was used; wrappers only rejected specified real command invocations. No tmux fallback was observed.
6. PASS, live: corrected live script and identity scenarios returned success only after typed exact-endpoint absence. The pre-fix live cleanup refusal returned failure and preserved its lab. Deterministic focused refusal checks also remained passing.

Focused deterministic verification: only test_kill_closes_workspace_directly_when_not_last, test_kill_refuses_unconfirmed_close and test_live_cleanup_guard_refuses_unconfirmed_close were executed from the existing test's definitions. All passed. No full suite, linter, formatter, static analysis, pipeline, push, PR or CI operation was run.

Isolation: fixture homes, Treehouse pool, Pi profile and sessions were under the worktree. Pi used copied credentials in a temporary local profile; credentials were not included in evidence and were removed with the lab. Only exact test-created workspace/surface identities were changed. Final typed absence checks confirmed the recorded workspaces were gone before temporary fixture cleanup.

This is the local test phase result, not a PR-readiness or remote-CI verdict.

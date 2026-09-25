#!/usr/bin/env bash
# Real Pi plus cmux launch-confirmation guard.
# Run explicitly with FM_CMUX_PI_LAUNCH_LIVE=1 from a process that can access
# cmux's socket.
# The test creates one exact fm-test- workspace through the normal scout path.
set -u

# shellcheck source=tests/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

TASK="test-cmux-pi-launch-$$"
LABEL="fm-$TASK"
LAB=
SPAWNED=0

cleanup() {
  local cleanup_ok=1 wsid=
  if [ "$SPAWNED" -eq 1 ] && [ -n "$LAB" ]; then
    if ! FM_HOME="$LAB" "$ROOT/bin/fm-teardown.sh" "$TASK" >/dev/null 2>&1; then
      cleanup_ok=0
    fi
  elif [ -n "$LAB" ]; then
    FM_HOME="$LAB"
    export FM_HOME
    if fm_backend_cmux_cli ping >/dev/null 2>&1; then
      for _ in $(seq 1 10); do
        wsid=$(fm_backend_cmux_workspace_id_for_label "$(fm_backend_cmux_scoped_title "$LABEL")")
        [ -z "$wsid" ] || break
        sleep 0.2
      done
    else
      cleanup_ok=0
    fi
    if [ -n "$wsid" ]; then
      # shellcheck source=tests/cmux-test-safety.sh
      . "$ROOT/tests/cmux-test-safety.sh"
      cmux_safe_close_workspace "$wsid" "$LABEL" >/dev/null 2>&1 || cleanup_ok=0
    else
      cleanup_ok=0
    fi
  fi
  if [ "$cleanup_ok" -eq 1 ]; then
    [ -z "$LAB" ] || rm -rf -- "$LAB"
  else
    printf 'cleanup could not confirm closure; preserving cmux Pi lab at %s\n' "$LAB" >&2
  fi
}
trap cleanup EXIT INT TERM

fm_live_gate opt-in FM_CMUX_PI_LAUNCH_LIVE jq treehouse pi python3
# shellcheck source=bin/backends/cmux.sh
. "$ROOT/bin/backends/cmux.sh"
ping_out=$(fm_backend_cmux_cli ping 2>&1) \
  || fail "FM_CMUX_PI_LAUNCH_LIVE=1 but the cmux socket is unavailable: $ping_out"

LAB=$(mktemp -d "${TMPDIR:-/tmp}/fm-cmux-pi-launch.XXXXXX") \
  || fail "could not create an isolated cmux Pi lab"
mkdir -p "$LAB/config" "$LAB/data/$TASK" "$LAB/projects/probe" "$LAB/state"
printf '%s\n' cmux > "$LAB/config/backend"
printf '%s\n' manual > "$LAB/config/backlog-backend"
touch "$LAB/state/.last-watcher-beat"

git -C "$LAB/projects/probe" init -q -b main \
  || fail "could not initialize the isolated probe repository"
git -C "$LAB/projects/probe" config user.email 'cmux-pi-test@example.invalid'
git -C "$LAB/projects/probe" config user.name 'cmux Pi test'
printf '%s\n' 'cmux Pi launch probe' > "$LAB/projects/probe/README.md"
git -C "$LAB/projects/probe" add README.md
git -C "$LAB/projects/probe" commit -qm 'fixture: initialize cmux Pi launch probe'

FM_HOME="$LAB" "$ROOT/bin/fm-brief.sh" "$TASK" probe --scout \
  || fail "could not scaffold the Pi probe brief"
python3 - "$LAB/data/$TASK/brief.md" "$LAB/data/$TASK/report.md" <<'PY'
from pathlib import Path
import sys

brief = Path(sys.argv[1])
report = sys.argv[2]
brief.write_text(brief.read_text().replace("{TASK}", f'''Run a cmux Pi launch probe.

Write exactly `cmux Pi launch probe passed` followed by a newline to `{report}`.
Then append `done [at=<epoch>]: cmux Pi launch probe passed` to the task status file as the instructions require.
Do not change project files or make a commit.'''))
PY

FM_HOME="$LAB" "$ROOT/bin/fm-spawn.sh" "$TASK" "$LAB/projects/probe" \
  --scout --harness pi --backend cmux \
  || fail "the real Pi cmux spawn did not confirm that Pi began processing its launch brief"
SPAWNED=1
assert_present "$LAB/state/$TASK.meta" "confirmed real Pi spawn did not publish metadata"

for _ in $(seq 1 60); do
  grep -Eq '^done( \[at=[0-9]+\])?: cmux Pi launch probe passed$' "$LAB/state/$TASK.status" 2>/dev/null && break
  sleep 1
done
assert_grep 'done' "$LAB/state/$TASK.status" \
  "real Pi did not complete the launch probe after spawn confirmation"
[ "$(cat "$LAB/data/$TASK/report.md" 2>/dev/null)" = 'cmux Pi launch probe passed' ] \
  || fail "real Pi did not process the probe instructions"
pass "a real cmux Pi scout reports processing the launch brief before fm-spawn returns success"

#!/usr/bin/env bash
# Public fm-spawn regression for cmux Pi launch confirmation.
# The fake cmux preserves the incident's masking condition: workspace creation
# returns an exact UUID pair while every current-window title listing stays empty.
# It can either emit Pi's real busy-event shape when the staged launch is
# submitted or leave the surface as an idle shell.
set -u

# shellcheck source=tests/fixtures.sh
. "$(dirname "${BASH_SOURCE[0]}")/fixtures.sh"

TMP_ROOT=$(fm_test_tmproot fm-cmux-pi-launch)
SUCCESS_ID="cmux-pi-ready-ok-$$"
FAILURE_ID="cmux-pi-ready-fail-$$"

cleanup_launch_tmp() {
  rm -rf -- "/tmp/fm-$SUCCESS_ID" "/tmp/fm-$FAILURE_ID"
  find /tmp -maxdepth 1 -type d \( -name "fm-$SUCCESS_ID+*" -o -name "fm-$FAILURE_ID+*" \) -exec rm -rf -- {} + 2>/dev/null || true
  fm_test_cleanup
}
trap cleanup_launch_tmp EXIT INT TERM

make_cmux_pi_fakebin() {  # <dir>
  local dir=$1 fakebin
  fakebin=$(fm_fakebin "$dir")
  fm_fake_exit0 "$fakebin" treehouse
  fm_test_fake_sleep_noop "$fakebin"

  cat > "$fakebin/pi" <<'SH'
#!/usr/bin/env bash
case "${1:-}" in
  --help) printf '%s\n' 'Usage: pi [--tui-mode <mode>]' ;;
  --version) printf '%s\n' 'pi 0.87.1' ;;
esac
exit 0
SH

  cat > "$fakebin/tmux" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${FM_FAKE_TMUX_FALLBACK_LOG:?}"
exit 88
SH

  cat > "$fakebin/cmux" <<'SH'
#!/usr/bin/env bash
set -u
printf '%s\n' "$*" >> "${FM_FAKE_CMUX_LOG:?}"
case "${1:-}" in
  version)
    printf '%s\n' 'cmux 0.64.17 (97) [fake]'
    exit 0
    ;;
  ping)
    printf '%s\n' 'PONG'
    exit 0
    ;;
esac
if [ "${1:-}" = workspace ] && [ "${2:-}" = list ]; then
  # The current-window projection remains empty after creation.
  printf '%s\n' '{"workspaces":[]}'
  exit 0
fi
if [ "${1:-}" = workspace ] && [ "${2:-}" = create ]; then
  printf '%s\n' '{"workspace_id":"aaaaaaaa-0000-0000-0000-000000000000","surface_id":"bbbbbbbb-1111-1111-1111-111111111111"}'
  exit 0
fi
case "${1:-}" in
  list-panes)
    printf '%s\n' '{"panes":[{"selected_surface_id":"bbbbbbbb-1111-1111-1111-111111111111","surface_ids":["bbbbbbbb-1111-1111-1111-111111111111"]}]}'
    ;;
  send)
    last=
    for arg in "$@"; do last=$arg; done
    printf '%s' "$last" > "${FM_FAKE_CMUX_LAST_LITERAL:?}"
    ;;
  send-key)
    last=
    for arg in "$@"; do last=$arg; done
    if [ "$last" = enter ] && grep -q '/launch\..*\.sh' "${FM_FAKE_CMUX_LAST_LITERAL:?}" 2>/dev/null; then
      : > "${FM_FAKE_CMUX_LAUNCH_MARKER:?}"
      if [ "${FM_FAKE_CMUX_START_PI:-0}" = 1 ]; then
        gen=$(cat "${FM_STATE_OVERRIDE:?}/${FM_FAKE_CMUX_ID:?}.busy-gen")
        "${FM_FAKE_ROOT:?}/bin/fm-busy-event.sh" apply \
          "$FM_STATE_OVERRIDE" "$FM_FAKE_CMUX_ID" busy \
          --gen "$gen" --source pi-ext --event agent-start >/dev/null
      fi
    fi
    ;;
  read-screen)
    text=$(printf '__FM_CMUX_CWD_BEGIN__\n%s\n__FM_CMUX_CWD_END__' "${FM_FAKE_CMUX_WT:?}")
    jq -n --arg text "$text" '{text:$text}'
    ;;
esac
exit 0
SH
  chmod +x "$fakebin/pi" "$fakebin/tmux" "$fakebin/cmux"
  printf '%s\n' "$fakebin"
}

make_case() {  # <name> <id>
  local name=$1 id=$2 dir home project copy fakebin
  dir="$TMP_ROOT/$name"
  home="$dir/home"
  project="$dir/project"
  copy="$dir/isolated-copy"
  fm_test_spawn_home "$home" pi
  printf '%s\n' manual > "$home/config/backlog-backend"
  fm_test_spawn_brief "$home" "$id" "Confirm a cmux Pi worker is processing this brief."
  fm_git_init_commit "$project"
  git clone -q "$project" "$copy" || fail "could not clone the isolated fixture copy"
  git -C "$copy" remote remove origin
  fakebin=$(make_cmux_pi_fakebin "$dir/fake")
  printf '%s\n' "$dir|$home|$project|$copy|$fakebin"
}

read_case() {
  IFS='|' read -r CASE_DIR HOME_DIR PROJECT_DIR COPY_DIR FAKEBIN_DIR <<EOF_CASE
$1
EOF_CASE
}

run_case_spawn() {  # <id> <emit-pi-event>
  local id=$1 emit=$2
  FM_FAKE_CMUX_LOG="$CASE_DIR/cmux.log" \
    FM_FAKE_CMUX_LAST_LITERAL="$CASE_DIR/last-literal" \
    FM_FAKE_CMUX_LAUNCH_MARKER="$CASE_DIR/launch-attempted" \
    FM_FAKE_CMUX_START_PI="$emit" FM_FAKE_CMUX_ID="$id" \
    FM_FAKE_CMUX_WT="$COPY_DIR" FM_FAKE_ROOT="$ROOT" \
    FM_FAKE_TMUX_FALLBACK_LOG="$CASE_DIR/tmux-fallback.log" \
    FM_CMUX_PI_READY_POLLS=2 FM_CMUX_PI_POLL_INTERVAL=0 \
    fm_test_run_spawn "$HOME_DIR" "$COPY_DIR" "$FAKEBIN_DIR" \
      "$id" "$PROJECT_DIR" --scout --harness pi --backend cmux
}

test_spawn_accepts_only_after_pi_agent_start() {
  local fixture out status record
  fixture=$(make_case success "$SUCCESS_ID")
  read_case "$fixture"
  out=$(run_case_spawn "$SUCCESS_ID" 1)
  status=$?
  expect_code 0 "$status" "spawn should accept the cmux endpoint after Pi reports agent_start"$'\n'"$out"
  assert_contains "$out" "spawned $SUCCESS_ID" "spawn did not report the confirmed Pi worker"
  assert_present "$HOME_DIR/state/$SUCCESS_ID.meta" "confirmed Pi spawn did not publish metadata"
  assert_present "$CASE_DIR/launch-attempted" "the staged Pi launch was not submitted"
  record=$(bash -c '. "$0/bin/fm-busy-lib.sh"; fm_busy_record_read "$1" "$2"' \
    "$ROOT" "$HOME_DIR/state" "$SUCCESS_ID")
  assert_contains "$record" 'busy pi-ext agent-start' \
    "confirmed Pi spawn did not retain the Pi extension event"
  assert_contains "$(cat "$CASE_DIR/cmux.log")" 'workspace create' \
    "spawn did not use the authoritative cmux workspace create response"
  assert_not_contains "$(cat "$CASE_DIR/cmux.log")" 'new-workspace' \
    "spawn fell back to the deprecated create-then-title-lookup command"
  [ ! -e "$CASE_DIR/tmux-fallback.log" ] || fail "explicit cmux spawn silently invoked tmux"
  pass "fm-spawn accepts a masked cmux workspace only after Pi reports processing the brief"
}

test_spawn_refuses_idle_shell_without_worker_record() {
  local fixture out status
  fixture=$(make_case failure "$FAILURE_ID")
  read_case "$fixture"
  out=$(run_case_spawn "$FAILURE_ID" 0)
  status=$?
  [ "$status" -ne 0 ] || fail "spawn accepted a cmux workspace whose Pi launch never started"
  assert_contains "$out" "Pi did not report processing its launch brief" \
    "spawn did not explain the missing Pi readiness evidence"
  assert_contains "$out" "idle shell" \
    "spawn did not identify the visible idle-shell symptom"
  assert_not_contains "$out" "spawned $FAILURE_ID" \
    "spawn pretended an unverified cmux endpoint was live"
  assert_absent "$HOME_DIR/state/$FAILURE_ID.meta" \
    "refused cmux Pi launch left a published worker record"
  assert_present "$CASE_DIR/launch-attempted" \
    "the failure arm did not reach staged Pi launch submission"
  assert_present "$COPY_DIR/README.md" \
    "refused cmux Pi launch lost the isolated project copy"
  assert_contains "$(cat "$CASE_DIR/cmux.log")" \
    'close-workspace --workspace aaaaaaaa-0000-0000-0000-000000000000' \
    "refused cmux Pi launch did not attempt exact endpoint cleanup"
  assert_grep 'idle shell' "$HOME_DIR/state/$FAILURE_ID.status" \
    "refused cmux Pi launch did not leave an actionable failure event"
  [ ! -e "$CASE_DIR/tmux-fallback.log" ] || fail "failed cmux spawn silently invoked tmux"
  pass "fm-spawn refuses an idle cmux shell, attempts exact cleanup, and preserves the unrecorded project copy"
}

test_spawn_accepts_only_after_pi_agent_start
test_spawn_refuses_idle_shell_without_worker_record

echo "# all cmux Pi launch confirmation tests passed"

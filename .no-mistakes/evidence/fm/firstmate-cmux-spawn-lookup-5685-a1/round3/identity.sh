#!/bin/bash
set -eu
ROOT=$PWD
export FM_HOME="$ROOT/.cmux-validation-r3/identity-home"
mkdir -p "$FM_HOME"
export PATH="$ROOT/.cmux-validation-r3/bin:/Applications/cmux.app/Contents/Resources/bin:$PATH"
. "$ROOT/bin/fm-backend.sh"
fm_backend_source cmux
. "$ROOT/tests/cmux-test-safety.sh"
label="fm-test-identity-$$"
other=471EE91D-7DB5-4988-A775-EF5C8F3EB785
cleanup_window=0
fm_backend_cmux_cli() {
  if [ "$1" = workspace ] && [ "$2" = create ]; then
    command cmux "$@" --window "$other"
  elif [ "$cleanup_window" = 1 ] && [ "$1" = workspace ] && [ "$2" = list ]; then
    command cmux "$@" --window "$other"
  else
    command cmux "$@"
  fi
}
ids=$(fm_backend_cmux_create_task "$label" "$ROOT/.cmux-validation-r3")
read -r ws sf <<< "$ids"
target="$ws:$sf"
printf 'created %s\n' "$target"
trap 'cleanup_window=1; cmux_safe_close_workspace "$target" "$label"' EXIT
listed=$(command cmux workspace list --json --id-format uuids | jq -r --arg ws "$ws" '.workspaces[] | select(.id==$ws) | .id')
[ -z "$listed" ]
fm_backend_cmux_target_ready "$target" "$label"
fm_backend_cmux_send_text_line "$target" 'echo real-exact-endpoint-proof' "$label"
sleep 0.5
capture=$(fm_backend_cmux_capture "$target" 20 "$label")
[[ "$capture" == *real-exact-endpoint-proof* ]]
echo 'PASS: real workspace absent from current-window projection remains usable by exact identity'
new=$(command cmux new-surface --workspace "$ws" --working-directory "$ROOT/.cmux-validation-r3" --command '/bin/bash --noprofile --norc' --focus false --json --id-format uuids)
printf '%s\n' "$new"
new_sf=$(printf '%s' "$new" | jq -r '.surface_id')
[ -n "$new_sf" ] && [ "$new_sf" != null ]
cleanup_window=1
cmux_refuse_if_unsafe "$target" "$label"
command cmux close-surface --workspace "$ws" --surface "$sf"
for i in {1..20}; do
  if ! fm_backend_cmux_surface_exists "$ws" "$sf"; then break; fi
  sleep 0.1
done
stale=$target
target="$ws:$new_sf"
marker="$ROOT/.cmux-validation-r3/wrong-endpoint-marker"
if fm_backend_cmux_send_literal "$stale" "touch '$marker'" "$label"; then exit 1; fi
if fm_backend_cmux_send_key "$stale" Enter "$label"; then exit 1; fi
if fm_backend_cmux_capture "$stale" 10 "$label"; then exit 1; fi
if fm_backend_cmux_kill "$stale" '' "$label"; then exit 1; fi
fm_backend_cmux_target_ready "$target" "$label"
[ ! -e "$marker" ]
echo 'PASS: stale surface refuses send, key, capture and cleanup while replacement remains live'
cmux_safe_close_workspace "$target" "$label"
fm_backend_cmux_workspace_confirmed_gone "$ws"
old=$target
cleanup_window=0
ids=$(fm_backend_cmux_create_task "$label" "$ROOT/.cmux-validation-r3")
read -r ws sf <<< "$ids"
target="$ws:$sf"
cleanup_window=1
if fm_backend_cmux_send_literal "$old" "touch '$marker'" "$label"; then exit 1; fi
if fm_backend_cmux_send_key "$old" Enter "$label"; then exit 1; fi
if fm_backend_cmux_capture "$old" 10 "$label"; then exit 1; fi
fm_backend_cmux_kill "$old" '' "$label"
fm_backend_cmux_target_ready "$target" "$label"
[ ! -e "$marker" ]
echo 'PASS: closed workspace never redirects to a live same-title replacement'
cmux_safe_close_workspace "$target" "$label"
fm_backend_cmux_workspace_confirmed_gone "$ws"
trap - EXIT
echo 'PASS: exact cleanup confirmed for both real test workspaces'

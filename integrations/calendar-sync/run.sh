#!/bin/zsh
# Runs one manaba → Google Calendar sync. launchd starts it on schedule; you can also run it by hand.
DIR="${0:A:h}"
LOG="$HOME/Library/Logs/manaba-calendar-sync.log"
CAL="mcp__claude_ai_Google_Calendar"
TIMEOUT_S=${MANABA_SYNC_TIMEOUT_S:-900}  # 15 minutes; a normal run takes under 2
started=$(date '+%Y-%m-%d %H:%M:%S')

log() { print -r -- "=== $started"$'\n'"$1"$'\n'"exit=$2" >> "$LOG"; }
notify() {
  osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title "manaba calendar sync"' \
    -e 'end run' "$1" 2>/dev/null
}
fail() { log "FAILED: $1" 1; notify "FAILED: $1"; exit 1; }

# Written by install.sh: PATH, MANABA_SYNC_CALENDAR_ID, MANABA_SYNC_MODEL, MANABA_SYNC_BUDGET_USD.
source "$DIR/config.env" 2>/dev/null || fail "cannot read $DIR/config.env. Run install.sh again."

# One run at a time: two overlapping runs would both see a task as new and both add it. install.sh and
# uninstall.sh take the same lock before they change files. It is released when this script exits.
zmodload zsh/system zsh/zselect
: >> "$DIR/.lock"
if ! zsystem flock -t 0 "$DIR/.lock" 2>/dev/null; then
  log "skipped: another sync is running" 0
  exit 0
fi

# Claude Code lets a tool call through when its hook cannot start, so never run without the guard.
[[ -x "$DIR/guard.sh" ]] || fail "$DIR/guard.sh is missing or not executable. Run install.sh again."

# Claude Code knows today's date but not the time; the job needs both to skip past deadlines.
prompt=$(<"$DIR/prompt.md")
prompt=${prompt//'{{NOW}}'/$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M')}

# Claude Code reads CLAUDE.md in the working folder and its parents. A new folder in the per-user temp
# folder has no such files, and no other user can write into it or its parents.
work=$(mktemp -d "$(getconf DARWIN_USER_TEMP_DIR)manaba-calendar-sync.XXXXXX") \
  || fail "cannot create a work folder"
claude_pid="" watchdog=""
# Clean up on every exit. If run.sh itself is stopped, stop Claude and the timer instead of leaving
# them running.
cleanup() {
  [[ -n "$claude_pid" ]] && kill $claude_pid 2>/dev/null
  [[ -n "$watchdog" ]] && kill $watchdog 2>/dev/null
  rm -rf "$work"
}
trap cleanup EXIT
trap 'exit 143' INT TERM HUP
cd "$work" || fail "cannot enter $work"

# --setting-sources "" loads no user, project or local settings, which keeps the user's own CLAUDE.md,
# hooks and plugins out of the job. --settings adds guard.sh as a hook on every calendar call.
# --tools keeps two built-in tools: Bash, and ToolSearch, which loads connector tool definitions on
# demand (without it every connector's tools go into each request and a run costs several times more).
# dontAsk refuses every Bash command and connector tool that is not in --allowedTools.
claude -p "$prompt" \
  --model "${MANABA_SYNC_MODEL:-sonnet}" \
  --setting-sources "" \
  --tools Bash,ToolSearch \
  --settings "$DIR/settings.json" \
  --permission-mode dontAsk \
  --allowedTools "Bash(manaba todo:*)" "Bash(manaba show:*)" "${CAL}__list_events" "${CAL}__create_event" \
  --max-budget-usd "${MANABA_SYNC_BUDGET_USD:-1}" \
  --no-session-persistence \
  --output-format text < /dev/null > "$work/output" 2>&1 &
claude_pid=$!

# A hung run (stalled network, a connector waiting for a login) would otherwise block every later run.
( trap - EXIT; zselect -t $(( TIMEOUT_S * 100 )); : > "$work/timed-out"; kill $claude_pid 2>/dev/null ) &
watchdog=$!
wait $claude_pid
rc=$?
claude_pid=""
kill $watchdog 2>/dev/null
watchdog=""

output=$(<"$work/output")
[[ -f "$work/timed-out" ]] && output+=$'\n'"FAILED: stopped after $(( TIMEOUT_S / 60 )) minutes"

# Report this run only: the log holds every earlier run too. Claude sometimes wraps the report line
# in markdown (bold, a list item, indentation), so allow and strip that.
summary=$(print -r -- "$output" | grep -E '^[[:space:]>*_`-]*(CREATED [0-9]+|FAILED:)' | tail -1 \
  | sed -E 's/^[[:space:]>*_`-]+//; s/[[:space:]*_`]+$//')
if [[ -z "$summary" ]]; then
  summary="FAILED: no report (exit $rc), see $LOG"
elif (( rc != 0 )) && [[ "$summary" != FAILED* ]]; then
  summary="FAILED: exit $rc, see $LOG"
fi
# Claude can report FAILED, or no report at all, and still exit 0; count both as a failure.
[[ "$summary" == FAILED* ]] && (( rc == 0 )) && rc=1
log "$output" $rc
notify "$summary"
exit $rc

#!/bin/zsh
# Runs one manaba → Google Calendar sync. launchd starts it on schedule; you can also run it by hand.
DIR="${0:A:h}"
LOG="$HOME/Library/Logs/manaba-calendar-sync.log"
CAL="mcp__claude_ai_Google_Calendar"
# Outside the install folder, so uninstall.sh can delete that folder while it holds the lock.
LOCK="$HOME/Library/Caches/manaba-calendar-sync.lock"
TIMEOUT_S=${MANABA_SYNC_TIMEOUT_S:-900}  # 15 minutes; a normal run takes under 2
started=$(date '+%Y-%m-%d %H:%M:%S')
have_lock=0

log() {
  print -r -- "=== $started"$'\n'"$1"$'\n'"exit=$2" >> "$LOG"
  # Keep the log small: once it passes 4000 lines, keep the newest 2000. Only the run holding the lock
  # does this, so no other run or guard.sh is writing to the log at the same time.
  if (( have_lock )) && (( $(wc -l < "$LOG") > 4000 )); then
    local tmp
    tmp=$(mktemp "$LOG.XXXXXX") && tail -n 2000 "$LOG" > "$tmp" && mv "$tmp" "$LOG"
  fi
}
notify() {
  osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title "manaba calendar sync"' \
    -e 'end run' "$1" 2>/dev/null
}
fail() { log "FAILED: $1" 1; notify "FAILED: $1"; exit 1; }

# Written by install.sh: PATH, MANABA_SYNC_CALENDAR_ID, MANABA_SYNC_MODEL, MANABA_SYNC_BUDGET_USD.
source "$DIR/config.env" 2>/dev/null || fail "cannot read $DIR/config.env. Run install.sh again."

# One run at a time: two overlapping runs would both see a task as new and both add it. install.sh and
# uninstall.sh take the same lock before they change files. It is released when this script exits.
# flock returns 1 for a busy lock and for a broken lock file alike, so check the file first.
zmodload zsh/system zsh/zselect
{ mkdir -p "${LOCK:h}"; : >> "$LOCK" } 2>/dev/null
[[ -r "$LOCK" && -w "$LOCK" ]] || fail "cannot use the lock file $LOCK"
if ! zsystem flock -t 0 "$LOCK" 2>/dev/null; then
  log "skipped: another sync or install.sh is running" 0
  notify "skipped: another sync or install.sh is running"
  exit 0
fi
have_lock=1

# Claude Code lets a tool call through when its hook cannot start, so never run without the guard:
# guard.sh must be executable and settings.json must load it.
[[ -x "$DIR/guard.sh" ]] || fail "$DIR/guard.sh is missing or not executable. Run install.sh again."
hook=$(/usr/bin/plutil -extract hooks.PreToolUse.0.hooks.0.command raw -o - "$DIR/settings.json" 2>/dev/null)
[[ -n "$hook" && "${${hook//\"/}:A}" == "$DIR/guard.sh" ]] \
  || fail "$DIR/settings.json does not load guard.sh. Run install.sh again."

# launchd starts a run missed during sleep as soon as the Mac wakes, often before Wi-Fi is back. Wait up
# to about 7 minutes for the manaba site; if it never answers, the run goes ahead and reports FAILED.
if [[ -n "$MANABA_SYNC_BASE_URL" ]]; then
  for attempt in {1..20}; do
    curl -s -o /dev/null --max-time 5 "$MANABA_SYNC_BASE_URL" && break
    zselect -t 1500
  done
fi

# Claude Code knows today's date but not the time; the job needs both to skip past deadlines.
prompt=$(<"$DIR/prompt.md")
prompt=${prompt//'{{NOW}}'/$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M')}

# Claude Code reads CLAUDE.md in the working folder and its parents. A new folder in the per-user temp
# folder has no such files, and no other user can write into it or its parents.
work=$(mktemp -d "$(getconf DARWIN_USER_TEMP_DIR)manaba-calendar-sync.XXXXXX") \
  || fail "cannot create a work folder"
claude_pid="" watchdog="" stopped=0 logged=0
# Claude runs in its own process group (set up below), so signalling the group reaches everything it
# started, even processes whose parent already exited. The tree catches any that left the group.
proc_tree() { local p; for p in $(pgrep -P $1 2>/dev/null); do proc_tree $p; done; print $1; }
stop_claude() {  # ask Claude and everything under it to stop, then kill what is left after $1 seconds
  local pids=($(proc_tree $claude_pid))
  kill -TERM -$claude_pid $pids 2>/dev/null
  zselect -t $(( $1 * 100 ))
  kill -KILL -$claude_pid $pids 2>/dev/null
}
# Clean up on every exit. If run.sh itself is stopped, stop Claude and the timer instead of leaving
# them running.
cleanup() {
  [[ -n "$claude_pid" ]] && stop_claude 2
  [[ -n "$watchdog" ]] && kill $watchdog 2>/dev/null
  if (( stopped && ! logged )); then  # record what the stopped run printed, so created events can be traced
    log "$(<"$work/output" 2>/dev/null)"$'\n'"FAILED: stopped by a signal" 143
    notify "FAILED: stopped by a signal, see $LOG"
  fi
  rm -rf "$work"
}
trap cleanup EXIT
trap 'stopped=1; exit 143' INT TERM HUP
cd "$work" || fail "cannot enter $work"

# perl's setpgrp gives Claude its own process group before exec; zsh cannot do that without a terminal.
in_own_group=()
[[ -x /usr/bin/perl ]] && in_own_group=(/usr/bin/perl -e 'setpgrp(0, 0); exec @ARGV or die "exec: $!\n"')

# --setting-sources "" loads no user, project or local settings, which keeps the user's own CLAUDE.md,
# hooks and plugins out of the job. --settings adds guard.sh as a hook on every Bash and calendar call.
# --tools keeps two built-in tools: Bash, and ToolSearch, which loads connector tool definitions on
# demand (without it every connector's tools go into each request and a run costs several times more).
# dontAsk refuses every Bash command and connector tool that is not in --allowedTools.
$in_own_group claude -p "$prompt" \
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
# The timer marks the run as timed out only if Claude is still running when it fires.
( trap - EXIT INT TERM HUP
  zselect -t $(( TIMEOUT_S * 100 ))
  kill -0 $claude_pid 2>/dev/null || exit 0
  : > "$work/timed-out"
  stop_claude 10 ) &
watchdog=$!
wait $claude_pid
rc=$?
# After a timeout, let the timer finish its forced kill; otherwise it is no longer needed. claude_pid
# stays set until then, so a signal arriving meanwhile still makes cleanup stop the process group.
if [[ -f "$work/timed-out" ]]; then wait $watchdog; else kill $watchdog 2>/dev/null; fi
watchdog=""
# Stop anything Claude left behind in its group (for example an MCP server that ignored the shutdown).
(( $#in_own_group )) && pgrep -g $claude_pid >/dev/null 2>&1 && stop_claude 2
claude_pid=""

# Report this run only: the log holds every earlier run too. Claude sometimes formats the report line
# as markdown (bold, heading, quote, list item), so strip that markup, and nothing else, before matching.
# Any FAILED line wins over a CREATED line, wherever it appears.
output=$(<"$work/output")
report=$(print -r -- "$output" \
  | sed -E 's/\*\*//g; s/`//g; s/^[[:space:]>#*-]*//; s/^[0-9]+\.[[:space:]]+//; s/[[:space:]*]+$//')
summary=$(print -r -- "$report" | grep -m1 -E '^FAILED:')
[[ -z "$summary" ]] && summary=$(print -r -- "$report" | grep -E '^CREATED [0-9]+' | tail -1)
if [[ -z "$summary" && -f "$work/timed-out" ]]; then
  summary="FAILED: stopped after $(( TIMEOUT_S / 60 )) minutes"
  output+=$'\n'"$summary"
elif [[ -z "$summary" ]]; then
  summary="FAILED: no report (exit $rc), see $LOG"
elif (( rc != 0 )) && [[ "$summary" != FAILED* ]]; then
  summary="FAILED: exit $rc, see $LOG"
fi
# Claude can report FAILED, or no report at all, and still exit 0; count both as a failure.
[[ "$summary" == FAILED* ]] && (( rc == 0 )) && rc=1
log "$output" $rc
logged=1
notify "$summary"
exit $rc

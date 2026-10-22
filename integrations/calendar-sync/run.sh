#!/bin/zsh
# Runs one manaba → Google Calendar sync. launchd starts it on schedule; you can also run it by hand.
DIR="${0:A:h}"
LOG="$HOME/Library/Logs/manaba-calendar-sync.log"
CAL="mcp__claude_ai_Google_Calendar"
started=$(date '+%Y-%m-%d %H:%M:%S')

log() { print -r -- "=== $started"$'\n'"$1"$'\n'"exit=$2" >> "$LOG"; }
notify() {
  osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title "manaba calendar sync"' \
    -e 'end run' "$1" 2>/dev/null
}

# Written by install.sh: PATH, MANABA_SYNC_CALENDAR_ID, MANABA_SYNC_MODEL, MANABA_SYNC_BUDGET_USD.
source "$DIR/config.env" || exit 1

# One run at a time: two overlapping runs would both see a task as new and both add it.
# The lock is released when this script exits, however it exits.
zmodload zsh/system
: >> "$DIR/.lock"
if ! zsystem flock -t 0 "$DIR/.lock" 2>/dev/null; then
  log "skipped: another sync is running" 0
  exit 0
fi

# Claude Code lets a tool call through when its hook cannot start, so never run without the guard.
if [[ ! -x "$DIR/guard.sh" ]]; then
  log "FAILED: $DIR/guard.sh is missing or not executable. Run install.sh again." 1
  notify "FAILED: guard.sh is missing, see $LOG"
  exit 1
fi

# Claude Code knows today's date but not the time; the job needs both to skip past deadlines.
prompt=$(<"$DIR/prompt.md")
prompt=${prompt//'{{NOW}}'/$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M')}

# Claude Code reads CLAUDE.md files in the working folder and its parents. The install folder is under
# the home folder, where a ~/CLAUDE.md would apply, so run from the system temp folder instead.
cd "${TMPDIR:-/tmp}" || exit 1

# --setting-sources project loads no settings from that folder, which keeps the user's own CLAUDE.md,
# hooks and plugins out of the job. --settings adds guard.sh as a hook on every calendar call.
# dontAsk refuses every tool that is not in --allowedTools.
output=$(claude -p "$prompt" \
  --model "${MANABA_SYNC_MODEL:-sonnet}" \
  --setting-sources project \
  --settings "$DIR/settings.json" \
  --permission-mode dontAsk \
  --allowedTools "Bash(manaba todo:*)" "Bash(manaba show:*)" "${CAL}__list_events" "${CAL}__create_event" \
  --max-budget-usd "${MANABA_SYNC_BUDGET_USD:-1}" \
  --no-session-persistence \
  --output-format text < /dev/null 2>&1)
rc=$?
log "$output" $rc

# Report this run only: the log holds every earlier run too.
summary=$(print -r -- "$output" | grep -E '^(CREATED|FAILED)' | tail -1)
(( rc != 0 )) && summary="FAILED: exit $rc, see $LOG"
notify "${summary:-finished without a report, see $LOG}"
exit $rc

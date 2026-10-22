#!/bin/zsh
# Runs one manaba → Google Calendar sync. launchd starts it on schedule; you can also run it by hand.
DIR="${0:A:h}"
LOG="$HOME/Library/Logs/manaba-calendar-sync.log"
CAL="mcp__claude_ai_Google_Calendar"

# Written by install.sh: PATH, MANABA_SYNC_CALENDAR_ID, MANABA_SYNC_MODEL, MANABA_SYNC_BUDGET_USD.
source "$DIR/config.env" || exit 1
cd "$DIR" || exit 1
started=$(date '+%Y-%m-%d %H:%M:%S')

# Claude Code knows today's date but not the time; the job needs both to skip past deadlines.
prompt=$(<"$DIR/prompt.md")
prompt=${prompt//'{{NOW}}'/$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M')}

# --setting-sources project loads no settings from this folder, which keeps the user's own CLAUDE.md,
# hooks and plugins out of the job. --settings adds guard.sh as a hook on every calendar call.
# dontAsk refuses every tool that is not in --allowedTools.
output=$(claude -p "$prompt" \
  --model "${MANABA_SYNC_MODEL:-sonnet}" \
  --setting-sources project \
  --settings "$DIR/settings.json" \
  --permission-mode dontAsk \
  --allowedTools "Bash(manaba todo:*)" "Bash(manaba show:*)" "Bash(manaba status:*)" \
                 "${CAL}__list_events" "${CAL}__create_event" \
  --max-budget-usd "${MANABA_SYNC_BUDGET_USD:-1}" \
  --no-session-persistence \
  --output-format text < /dev/null 2>&1)
rc=$?
print -r -- "=== $started"$'\n'"$output"$'\n'"exit=$rc" >> "$LOG"

# Report this run only: the log holds every earlier run too.
summary=$(print -r -- "$output" | grep -E '^(CREATED|FAILED)' | tail -1)
(( rc != 0 )) && summary="FAILED: exit $rc, see $LOG"
osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title "manaba calendar sync"' \
  -e 'end run' "${summary:-finished without a report, see $LOG}" 2>/dev/null
exit $rc

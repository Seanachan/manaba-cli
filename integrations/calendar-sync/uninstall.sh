#!/bin/zsh
# Stops the launchd job and removes the installed files. The log is kept.
LABEL="io.github.seanachan.manaba-calendar-sync"
DOMAIN="gui/$(id -u)"

# Deleting guard.sh under a running sync would leave its last calendar calls unchecked.
job_state=$(launchctl print "$DOMAIN/$LABEL" 2>/dev/null || true)
if [[ "$job_state" == *'state = running'* ]]; then
  print -u2 "error: a sync is running right now. Run uninstall.sh again when it has finished (about 2 minutes)"
  exit 1
fi

if launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null; then
  echo "Stopped $LABEL"
else
  echo "$LABEL was not loaded"
fi
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
rm -rf "$HOME/.local/share/manaba-calendar-sync"
echo "Removed. The log is still at ~/Library/Logs/manaba-calendar-sync.log"

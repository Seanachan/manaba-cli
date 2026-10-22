#!/bin/zsh
# Stops the launchd job and removes the installed files. The log is kept.
LABEL="io.github.seanachan.manaba-calendar-sync"

if launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null; then
  echo "Stopped $LABEL"
else
  echo "$LABEL was not loaded"
fi
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
rm -rf "$HOME/.local/share/manaba-calendar-sync"
echo "Removed. The log is still at ~/Library/Logs/manaba-calendar-sync.log"

#!/bin/zsh
# PreToolUse hook for the sync job. Allows a Google Calendar call only on the configured calendar and
# only with the fields the job needs, so text in a manaba page cannot make Claude invite guests or touch
# other calendars. Claude Code passes the call as JSON on stdin; exit 2 blocks it and tells Claude why.
DIR="${0:A:h}"
source "$DIR/config.env"
call=$(cat)

verdict=$(osascript -l JavaScript - "${MANABA_SYNC_CALENDAR_ID:-}" "$call" 2>/dev/null <<'JS'
function run(argv) {
  const calendarId = argv[0];
  const call = JSON.parse(argv[1]);
  const tool = String(call.tool_name || "").split("__").pop();
  const input = call.tool_input || {};
  const allowedFields = {
    list_events: ["calendarId", "startTime", "endTime", "fullText", "pageSize", "pageToken", "orderBy", "timeZone"],
    create_event: ["calendarId", "summary", "startTime", "endTime", "timeZone", "location", "description",
                   "colorId", "overrideReminders", "useDefaultReminders"],
  }[tool];
  if (!calendarId) return "no calendar configured";
  if (!allowedFields) return `${tool} is not allowed`;
  const extra = Object.keys(input).filter((key) => !allowedFields.includes(key));
  if (extra.length) return `fields not allowed: ${extra.join(", ")}`;
  // An omitted calendarId means the primary calendar, so require it to be spelled out.
  if (!input.calendarId) return `calendarId is missing: pass calendarId "${calendarId}"`;
  if (input.calendarId !== calendarId) return `only calendar "${calendarId}" may be used: pass exactly that calendarId`;
  return "ok";
}
JS
)

[[ "$verdict" == ok ]] && exit 0
print -u2 "blocked by manaba-calendar-sync guard: ${verdict:-could not read the tool call}"
exit 2

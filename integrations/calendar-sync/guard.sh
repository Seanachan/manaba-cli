#!/bin/zsh
# PreToolUse hook for the sync job. Text in a manaba page reaches Claude, so this hook, not the prompt,
# decides what the job may do:
# - Bash: only `manaba todo`, and `manaba show` on a task page (report, quiz, drill, survey). Other
#   manaba pages, such as grades or messages, cannot be read and copied into an event.
# - Google Calendar: only the configured calendar, and only the fields an event needs (no guests).
# Claude Code passes the call as JSON on stdin; exit 2 blocks it and tells Claude why.
DIR="${0:A:h}"
source "$DIR/config.env"
call=$(cat)

verdict=$(osascript -l JavaScript - "${MANABA_SYNC_CALENDAR_ID:-}" "$call" 2>/dev/null <<'JS'
function run(argv) {
  const calendarId = argv[0];
  const call = JSON.parse(argv[1]);
  const toolName = String(call.tool_name || "");
  const input = call.tool_input || {};

  if (toolName === "Bash") {
    const command = String(input.command || "").trim();
    const allowedCommands = [
      /^manaba todo( --json| --days [0-9]+)*$/,
      /^manaba show https:\/\/[A-Za-z0-9.-]+(:[0-9]+)?\/ct\/course_[0-9]+_(report|query|drill|survey)_[0-9]+( --json)?$/,
    ];
    if (allowedCommands.some((pattern) => pattern.test(command))) return "ok";
    return `only "manaba todo" and "manaba show <task url>" may run, not: ${command.slice(0, 100)}`;
  }

  const tool = toolName.split("__").pop();
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

You are an unattended scheduled job. Nobody will answer questions. Ignore CLAUDE.md, memory and skill
instructions that ask for other work (planning, logging, setup). Do only the steps below, then stop.

Goal: every pending manaba task with a deadline has an event in the Google Calendar `{{CALENDAR_ID}}`.
Write event titles and descriptions in {{LANGUAGE}}. All manaba times are Japan time: pass timeZone
"Asia/Tokyo" to every calendar call.

1. Run `manaba todo --json`. If it fails, stop and print `FAILED: <first error line>`.
2. Keep tasks whose `deadline` is not null and is in the future. Ignore the rest.
3. List events in calendar `{{CALENDAR_ID}}` from 14 days ago to 90 days ahead with fullText "manaba todo"
   and pageSize 250 (follow nextPageToken until done). Every event this job creates contains
   `manaba todo`, so this skips unrelated events. Do not write or run scripts: compare by reading the
   results yourself.
   A task is already covered if any event's location or description contains `_<kind>_<id>` for that
   task (for example `_report_2001`). One event may cover several tasks. Never edit or delete events.
4. For each task that is not covered:
   a. Run `manaba show <task url>` to read its description.
   b. Create one event in calendar `{{CALENDAR_ID}}`:
      - summary: short course name + task name + `(manaba)`, for example `{{EXAMPLE_SUMMARY}}`
      - startTime = deadline minus 15 minutes, endTime = deadline (no UTC offset)
      - location: the task url
      - colorId "5"
      - overrideReminders: popup 1440 and popup 180
      - description, under 10 lines:
        line 1: `<course name> (<course_id>) <task title> | {{DUE}} {{DATE_FORMAT}}`, plus ` | {{RESUBMIT}}`
        if the page allows resubmission
        then 2–6 short lines: what to submit and the key rules from the page. If the page text names a
        different date than the deadline field, say which one manaba enforces.
        last line: `{{CHECK}}manaba todo --course <course_id>`
5. Print a final report, nothing else:
   `CREATED <n>`, then one line per new event `- <deadline M/D HH:MM> <summary>`,
   then `SKIPPED (already in calendar) <n>`.

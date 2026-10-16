## What and why

<!-- One or two sentences. Link the issue if there is one. -->

## How it was tested

<!-- e.g. new fixture + parser test; ran `manaba todo` against <university> manaba. -->

## Checklist

- [ ] No new write paths: no POST/PUT/PATCH/DELETE, no form submission outside the SSO login, no state-changing GET links
- [ ] Fixtures are anonymized: no real names, student ids, usernames, course or task titles, cookies or tokens
- [ ] Existing `--json` keys are unchanged (new keys are fine)
- [ ] `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` pass
- [ ] Docs updated if behaviour or flags changed (README / CONTRIBUTING)

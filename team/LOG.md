# Session log

One entry per agent turn, **newest first**. Never edit or delete old entries (append a
correction in a new entry instead). `tools/handoff.py` reads the top entry.

Template (copy it to the top, below this header block):

```
## YYYY-MM-DD — <claude|opencode> — <short title>
**Request:** what the user asked (one or two lines, English).
**Done:** what changed and why; list touched files/areas.
**Verified:** tests run and results; manual checks.
**Not done / open:** anything left, unverified, or blocked; questions for the user.
**Next:** the single most useful next step (agent or user).
```

<!-- entries below -->

## 2026-11-19 — claude — Team workflow for Claude Code + OpenCode
**Request:** From now on Claude Code and OpenCode alternate on this project; the repo must contain
everything, fully explained, plus a way to pass information between agents (what changed, what is
left, shared project memory).
**Done:** Added `AGENTS.md` (shared rules, read by OpenCode), `CLAUDE.md` (imports AGENTS.md and
STATUS), `opencode.json` (auto-loads `team/STATUS.md`), `team/` (STATUS, LOG, DECISIONS, CONTEXT,
ARCHITECTURE, USER_STEPS, README) and `tools/handoff.py` (start/end/status + lock + secret scan).
Moved all knowledge from Claude's private memory into `team/`. README links the team docs.
**Verified:** 37 unit tests pass; `handoff.py start/end/status` exercised; OpenCode 2.2.5 binary
checked: it loads `AGENTS.md` (walking up from cwd) and `instructions` from project `opencode.json`;
it does not read `CLAUDE.md`.
**Not done / open:** Deployment still waits for the user's account setup (STATUS T-09).
**Next:** User does `team/USER_STEPS.md` Part 1, then any agent does T-10.

## 2026-11-06 — claude — Initial implementation (reconstructed entry)
**Request:** Build WOA: free Alexa Smart Home skill for Wake on LAN (Lambda + DynamoDB + SAM,
LWA account linking, GitHub Pages setup page, skill package, tests), IT + EN.
**Done:** All code in `src/woa/`, tests, `template.yaml`, `docs/` site, `skill-package/`, icons.
Created public repo `ccccri/woa` and enabled GitHub Pages from `/docs`. Commit c0dbcdd.
**Verified:** 37 tests (incl. DynamoDB with moto) pass; cfn-lint clean; JS syntax checked;
Pages URLs return 200.
**Not done / open:** Nothing deployed (needs user accounts). See STATUS "Unverified assumptions".
**Next:** User account setup (USER_STEPS Part 1).

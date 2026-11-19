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

## 2026-11-19 — claude — Guided Amazon Developer setup in the browser; deploy script
**Request:** The user found the written instructions confusing and asked to be guided step by step
while the agent watches the screen (Helium browser with the Claude in Chrome extension).
**Done:** Watched the screens and guided: LWA security profile `WOA` (privacy URL, Allowed Origins
`https://ccccri.github.io`), skill "WOA: Wake On Alexa" (Smart Home, Provision your own, it-IT +
en-US + en-GB), Permissions → Send Alexa Events. All IDs (public) recorded in CONTEXT. The user
clicked every save/create button. Added `tools/deploy.sh` (asks the skill-messaging secret
hidden, deploys to eu-north-1, prints outputs) and rewrote USER_STEPS 1.5 around it.
**Verified:** Screens checked after each step; `bash -n tools/deploy.sh`; tests pass.
**Not done / open:** A page search exposed a fragment of the LWA client secret to the agent tool
(not stored) → T-18 reset before publishing. Deploy not run yet. Lesson: on Amazon console pages
use screenshots/zoom, not `find`/`read_page`, because hidden secrets are in the DOM.
**Next:** User runs `tools/deploy.sh`, gives `SkillFunctionArn` + `ApiUrl`; then T-10 and Part 2.

## 2026-11-19 — claude — Amazon accounts: personal developer, family account as beta tester
**Request:** The user signed up to AWS with the personal Amazon account while the Echo devices are on
the family account; asked if that is fine and what to do on developer.amazon.com.
**Done:** Explained (in chat) USER_STEPS 1.2-1.4. User chose: developer account on the personal
account, family account invited as beta tester (D-015). Updated CONTEXT, USER_STEPS (intro, new
Part 2 step 6 beta test, Part 3 uses the family account), STATUS.
**Verified:** Docs only; 37 tests pass.
**Not done / open:** Beta testing for Smart Home skills before certification is assumed, not verified.
**Next:** User does USER_STEPS 1.2-1.4 and sends Skill ID + the two client IDs (never secrets).

## 2026-11-19 — claude — AWS account setup, Agent Toolkit, region change to eu-north-1
**Request:** The user signed up to AWS (new AWS experience) and asked to follow AWS's "Agent
Toolkit" setup prompt; asked how MFA works. Chose to install the toolkit too.
**Done:** Installed AWS CLI 2.41.1 and uv (user-local); user logged in with `aws login --profile woa`
(region eu-north-1); installed the Agent Toolkit for Claude Code and OpenCode with auto-update off
and pointed `aws-mcp` at profile `woa`; installed SAM CLI 1.173.0. Did not add AWS rules to this
repo. Found that the AWS project is locked to eu-north-1: added D-013 (deploy there, test it in
T-17) and D-014 (AWS access rules for agents); updated STATUS, CONTEXT (AWS account section),
USER_STEPS 1.1/1.5, AGENTS.md (AWS rule, deploy command), ARCHITECTURE, README, privacy policy
(Sweden) and the `config.js` placeholder.
**Verified:** `aws sts get-caller-identity` OK; `aws-mcp` connected in both Claude Code and
OpenCode; `aws agent-toolkit list-available-skills` OK; free plan active (USD 100, until
2027-05-19); 37 tests pass.
**Not done / open:** Nothing deployed yet. Unverified whether Alexa accepts a Stockholm Lambda
(T-17). The free plan ends 2027-05-19 (see Known risks).
**Next:** User does USER_STEPS 1.2-1.4 (Amazon Developer, LWA profile, skill), then T-17.

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

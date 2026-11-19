# Project status

**Last updated:** 2026-11-19 by claude
**Phase:** 1 — waiting for the user's account setup (code is written, not deployed yet)

## Next step

The **user** completes `team/USER_STEPS.md` Part 1 (AWS, Amazon Developer, Login with Amazon
security profile, skill creation, `sam deploy`). Then the user gives an agent:
`SkillFunctionArn`, `ApiUrl` and the LWA **client ID**. The agent then does task T-10.

## Tasks

Status: `[x]` done · `[ ]` to do · `[~]` in progress · `[!]` blocked. Owner: `user`, `agent`
(either agent) or a specific agent.

### Done
- [x] T-01 agent — Lambda backend: Discovery, AcceptGrant, deferred TurnOn + WakeUp, TurnOff error, ReportState (`src/woa/`).
- [x] T-02 agent — Setup page API (Lambda Function URL) with Login with Amazon token check.
- [x] T-03 agent — Unit tests (37) with sample Alexa directives; DynamoDB test with moto.
- [x] T-04 agent — SAM template (`template.yaml`), validated with cfn-lint.
- [x] T-05 agent — GitHub Pages site: home, setup page, privacy, terms (EN + IT), icons 108/512.
- [x] T-06 agent — Skill package: `skill.json`, account linking JSON, certification testing notes.
- [x] T-07 agent — Public repo `ccccri/woa`, GitHub Pages from `/docs` (live).
- [x] T-08 claude — Team workflow for Claude Code + OpenCode (`AGENTS.md`, `team/`, `tools/handoff.py`).

### Waiting for the user
- [ ] T-09 user — `team/USER_STEPS.md` Part 1: accounts, LWA profile, skill, deploy.
- [ ] T-11 user — `team/USER_STEPS.md` Part 2: skill endpoint, account linking, enable skill on own Echo.
- [ ] T-12 user — Decide: email address for the privacy policy contact (now only GitHub issues).
- [ ] T-13 user — Decide: keep the name "WOA: Wake On Alexa" or use a fallback (see DECISIONS D-011).

### To do (agents)
- [ ] T-10 agent — After deploy: put LWA client ID + `ApiUrl` in `docs/config.js`, the Lambda ARN in
      `skill-package/skill.json`, commit, push (user asked for GitHub Pages), verify the setup page.
- [ ] T-14 agent — Guide the first real test with the user's Echo Dot + PC (`team/USER_STEPS.md` Part 3);
      check CloudWatch logs with the user; fix what the real Alexa traffic reveals (see "Unverified").
- [ ] T-15 agent — Prepare certification: final listing texts, screenshots/notes, run Alexa
      "Validation" tab checks, `team/USER_STEPS.md` Part 4.
- [ ] T-16 agent (optional) — Second regional endpoint in `us-east-1` for en-US users, only if
      the region fallback (D-006) turns out to be insufficient.

## Unverified assumptions (check during the first real test, T-14)

- LWA `tokeninfo` returns `user_id`, `aud` and `exp` (seconds left) as coded in `lwa.py`.
- Alexa accepts MAC addresses with dashes `C8-7F-54-0B-30-C5` (docs example uses dashes).
- The Login with Amazon JS SDK (`sdk/na/login1.js`, default region) gives the same `user_id`
  as account linking for an Italian Amazon account.
- `NOT_SUPPORTED_IN_CURRENT_MODE` is an acceptable answer to TurnOff.
- `Alexa.EndpointHealth` version `"3"` is still accepted (newer docs show 3.1).
- AcceptGrant must use the "Alexa Skill Messaging" client credentials (not the LWA profile).
- The Alexa console accepts the eu-west-1 Lambda ARN also as the North America endpoint (USER_STEPS 2.1).

## Known risks

- Skill name containing "Alexa" may be rejected at certification (D-011).
- en-US users officially belong to the North America region (us-east-1); WOA relies on the
  gateway region fallback (D-006).

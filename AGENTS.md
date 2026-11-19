# AGENTS.md — WOA: Wake On Alexa

This file is the shared instruction manual for **every AI agent** working on this repository.
Two agents work on WOA as a team, **taking turns** on the user's requests:

- **Claude Code** (reads `CLAUDE.md`, which imports this file)
- **OpenCode** (reads this file directly, plus the files listed in `opencode.json`)

Everything an agent needs to know lives **inside this repository**. Agent-private memories
(Claude's `~/.claude/...`, OpenCode's session history) are not shared, so never rely on them
alone: if something matters for the project, write it in `team/`.

---

## 1. Start here (every session, before touching anything)

```sh
cd ~/Claude/woa
python3 tools/handoff.py start --agent <claude|opencode>
```

It prints the current status, the last handoff note, the commits made since that note and any
uncommitted changes, and marks you as the active agent. Then read, in this order:

1. `team/STATUS.md` — where the project is, the task list, what is next, what is blocked.
2. The top entry of `team/LOG.md` — what the previous agent did and left for you.
3. `team/DECISIONS.md` — settled decisions. Do not reopen them without a new reason; if you
   change one, add a new decision that supersedes it.
4. `team/CONTEXT.md` — the user, their hardware/network, preferences, glossary, references.
5. `team/ARCHITECTURE.md` — how the code works (read the parts you are going to change).

If `start` warns that the other agent is still active or left uncommitted work, **stop and tell
the user** instead of overwriting it.

## 2. Finish here (every session, before answering the user for the last time)

1. Run the tests: `python3 -m unittest discover -s tests` (must pass).
2. Update `team/STATUS.md` (task list, "Next step", "Last updated").
3. Add a new entry **at the top** of `team/LOG.md` (template inside the file).
4. Add to `team/DECISIONS.md` any decision you made, with the reason.
5. Run `python3 tools/handoff.py end --agent <claude|opencode>`; it checks tests, the log,
   secrets, and releases the active-agent lock.
6. Commit (see §6). The next agent finds your work through the log and the git history.

A turn is not finished until the log entry is written: the other agent cannot ask you questions.

## 3. Language rules (from the user, mandatory)

- **Chat with the user: Italian.**
- **Everything in the repository is English**: code, comments, commit messages, docs, `team/`
  files, UI strings (except the Italian translations the product ships, e.g. `docs/assets/i18n.js`,
  the `lang="it"` blocks and the it-IT skill listing).

## 4. What the project is

A free, open source (MIT), forever-free Alexa **Smart Home** skill: "Alexa, turn on the computer"
from any Echo or the Alexa app wakes a PC with Wake on LAN. It uses the official
`Alexa.WakeOnLANController` interface, so the **Echo on the PC's LAN sends the magic packet**;
no extra device at home. Replaces wolskill.com (now paid). Locales: it-IT, en-US, en-GB.
Only power **on**; there is no power off.

- Backend: AWS Lambda (Python, stdlib only) + DynamoDB, `eu-west-1` (D-016), deployed with AWS SAM.
  A cost guard (budget + kill switch) is part of the stack and must never be removed.
  Must stay inside the AWS always-free tier.
- Account linking: Login with Amazon (scope `profile:user_id`).
- Setup page: static site in `docs/` on GitHub Pages (https://ccccri.github.io/woa/).
- Repo: https://github.com/ccccri/woa (public), local path `~/Claude/woa`.

## 5. Repository map

| Path | What |
| --- | --- |
| `AGENTS.md` | This file: rules and workflow for all agents |
| `CLAUDE.md` | Claude Code entry point (imports this file) |
| `opencode.json` | OpenCode project config (auto-loads `team/STATUS.md`) |
| `team/` | **Shared project memory**: status, log, decisions, context, architecture, user steps |
| `tools/handoff.py` | Session start/end helper for the agent handoff |
| `tools/make_icons.py` | Regenerates `docs/assets/icon-108.png` and `icon-512.png` |
| `src/woa/` | Lambda code (see `team/ARCHITECTURE.md`) |
| `tests/` | Unit tests (`unittest`) and sample Alexa directives in `tests/events/` |
| `template.yaml` | AWS SAM template |
| `docs/` | GitHub Pages site: home, setup page, privacy, terms, icons, `config.js` |
| `skill-package/` | Skill manifest, account linking settings, certification testing notes |

## 6. Working rules

- **One agent at a time.** The user alternates requests between agents. Do only what the
  current request asks plus the bookkeeping in §2; leave other ideas as tasks in `STATUS.md`.
- **The user owns all accounts.** Never create, sign in to, or change anything on the user's
  Amazon Developer, AWS, Login with Amazon or certification accounts. Write step-by-step
  instructions in `team/USER_STEPS.md` and tell the user in chat what to do.
- **AWS access (D-014):** both agents have the AWS CLI profile `woa` and the `aws-mcp` MCP
  server. Read-only checks are fine; **ask the user before creating, changing or deleting any
  AWS resource**, and never deploy secrets on their behalf. The project can only use
  the regions allowed by its SCP; see D-016 and `team/CONTEXT.md`.
- **No secrets in the repo, logs or chat.** Client secrets, AWS keys and tokens are entered by
  the user directly (e.g. `sam deploy --guided`). Client IDs, skill ID, ARNs and URLs are not
  secret and can be committed. `handoff.py end` scans for common secret patterns.
- **Tests first-class.** Every behaviour change in `src/` needs a unit test. Keep the Lambda
  code standard-library only (boto3 is provided by the runtime). Tests must run with plain
  `python3 -m unittest discover -s tests` (no pytest, no network).
- **Free tier is a requirement**, not a nice-to-have: no API Gateway, no Secrets Manager, no
  NAT, no paid add-ons. DynamoDB stays PROVISIONED within 25 RCU/WCU total.
- **Commits:** small, English, imperative subject. End the message with a trailer naming the
  agent and model, e.g. `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` or
  `Co-Authored-By: OpenCode (<model>) <noreply@opencode.ai>`. Commit locally at the end of every
  turn. **Push to GitHub only when the user asks** (GitHub Pages serves `docs/` from `main`).
- Do not rewrite git history (`push --force`, `rebase` of pushed commits, `reset --hard`).
- When docs and code disagree, fix the docs in the same turn.
- Verify Amazon/AWS facts against official docs before relying on them, and record the source
  URL in `team/CONTEXT.md` (§References) or the decision entry.

## 7. Commands

```sh
python3 -m unittest discover -s tests -v          # unit tests (DynamoDB test skipped without moto)
python3 tools/handoff.py start --agent claude      # begin a turn
python3 tools/handoff.py end --agent claude        # end a turn (checks + unlock)
python3 tools/handoff.py status                    # read-only summary
python3 tools/make_icons.py                        # regenerate icons (needs Pillow)

# Optional full checks in a throwaway venv:
python3 -m venv /tmp/woa-venv && /tmp/woa-venv/bin/pip install cfn-lint "moto[dynamodb]" boto3
/tmp/woa-venv/bin/cfn-lint template.yaml
AWS_DEFAULT_REGION=eu-west-1 AWS_ACCESS_KEY_ID=x AWS_SECRET_ACCESS_KEY=x \
  /tmp/woa-venv/bin/python -m unittest discover -s tests

# Deploy (the USER runs it, it asks for secrets):
tools/deploy.sh      # eu-west-1, asks the secret and the alert email (D-016)

# AWS CLI (profile woa, region eu-north-1; renew with: aws login --profile woa)
aws sts get-caller-identity --profile woa
```

## 8. Code conventions

- Python 3.14 runtime (`python3.14`, arm64); code must also run on the local Python (3.15).
- Modules in `src/woa/` take their dependencies as arguments (`Services`) so tests inject fakes
  from `tests/fakes.py`. Never call AWS or the network from tests.
- Alexa message builders live only in `alexa.py`; handlers never hand-write JSON envelopes.
- Never log tokens, MAC addresses or user IDs (the privacy policy promises it).
- Front end: plain HTML/CSS/JS, no build step, no frameworks. Build DOM with `textContent`
  (never `innerHTML` with user data). Every UI string goes through `docs/assets/i18n.js` in both
  English and Italian.
- If you change what data is stored or how, update `docs/privacy.html` (both languages).

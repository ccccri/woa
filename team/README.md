# team/ — shared project memory

Claude Code and OpenCode take turns on this project. Neither can see the other's chat or
private memory, so **this folder is the memory of the project**. Rules are in `../AGENTS.md`.

| File | Purpose | When to update |
| --- | --- | --- |
| `STATUS.md` | Current phase, next step, task list (T-NN), unverified assumptions, risks | Every turn |
| `LOG.md` | Journal of agent turns, newest first | Every turn (new entry at the top) |
| `DECISIONS.md` | Settled decisions (D-NNN) with reasons and sources | When you decide something |
| `CONTEXT.md` | User, hardware/network, preferences, glossary, verified references | When you learn something durable |
| `ARCHITECTURE.md` | How the code works: flows, API, data model, config, security, tests | When code behaviour changes |
| `USER_STEPS.md` | Step-by-step guide for what only the user can do (accounts, deploy, tests) | When the procedure changes |

Turn protocol (details in AGENTS.md §1-§2):

```sh
python3 tools/handoff.py start --agent <claude|opencode>   # read status, last log, new commits; take the lock
# ... work ...
python3 tools/handoff.py end --agent <claude|opencode>     # tests, log check, secret scan; release the lock
git add -A && git commit                                    # with the agent trailer
```

Task IDs (`T-NN`) and decision IDs (`D-NNN`) are never reused; refer to them in log entries and
commit messages so the history stays searchable (`git log --grep T-10`).

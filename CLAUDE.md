# CLAUDE.md

Claude Code entry point. The shared rules for all agents (Claude Code and OpenCode) are in
`AGENTS.md`; the shared project memory is in `team/`. Follow them exactly.

@AGENTS.md
@team/STATUS.md

## Claude Code specifics

- Begin each turn with `python3 tools/handoff.py start --agent claude` and end it with
  `python3 tools/handoff.py end --agent claude` (see AGENTS.md §1-§2).
- Claude's private memory (`~/.claude/projects/.../memory/woa-alexa-project.md`) only points to
  this repository. Write project knowledge in `team/`, never only in private memory.
- Commit trailer: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

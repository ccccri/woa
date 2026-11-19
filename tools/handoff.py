#!/usr/bin/env python3
"""Turn handoff helper for the agents working on WOA (Claude Code and OpenCode).

  python3 tools/handoff.py start --agent claude    begin a turn: show context, take the lock
  python3 tools/handoff.py end --agent claude      end a turn: run checks, release the lock
  python3 tools/handoff.py status                  read-only summary

The lock file (team/.active, git-ignored) records which agent is working, so the other agent
can tell when a turn was left unfinished. See AGENTS.md sections 1-2.
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEAM = os.path.join(ROOT, "team")
LOCK = os.path.join(TEAM, ".active")
STATUS = os.path.join(TEAM, "STATUS.md")
LOG = os.path.join(TEAM, "LOG.md")
AGENTS = ("claude", "opencode")

TRAILERS = {
    "claude": "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>",
    "opencode": "Co-Authored-By: OpenCode (<model>) <noreply@opencode.ai>",
}

# Patterns that must never be committed. Placeholders like REPLACE_ME are fine.
SECRET_PATTERNS = [
    ("AWS access key ID", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("AWS secret key assignment", re.compile(r"aws_secret_access_key\s*[=:]\s*[A-Za-z0-9/+]{30,}", re.I)),
    ("LWA client secret", re.compile(r"amzn1\.oa2-cs\.v1\.[0-9a-f]{20,}")),
    ("LWA access/refresh token", re.compile(r"\bAtz[ar]\|[A-Za-z0-9_\-|]{20,}")),
    ("Private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Client secret value", re.compile(
        r"""["']?client_?secret["']?\s*[:=]\s*["'](?!REPLACE_ME)[^"'\s]{16,}["']""", re.I)),
]
SKIP_SCAN = {"tools/handoff.py"}  # contains the patterns themselves

BOLD, RED, YELLOW, GREEN, RESET = "\033[1m", "\033[31m", "\033[33m", "\033[32m", "\033[0m"
if not sys.stdout.isatty():
    BOLD = RED = YELLOW = GREEN = RESET = ""


def git(*args):
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return out.stdout.rstrip()


def today():
    return dt.date.today().isoformat()


def title(text):
    print(f"\n{BOLD}== {text} =={RESET}")


def warn(text):
    print(f"{YELLOW}WARNING:{RESET} {text}")


def fail(text):
    print(f"{RED}FAIL:{RESET} {text}")


def ok(text):
    print(f"{GREEN}OK:{RESET} {text}")


# --- Reading the team files ---------------------------------------------------

def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def top_log_entry():
    """Return (header_line, full_text) of the newest LOG.md entry, or (None, None)."""
    text = read(LOG).split("<!-- entries below -->", 1)[-1]
    parts = re.split(r"(?m)^(?=## \d{4}-\d{2}-\d{2} )", text)
    entries = [p.strip() for p in parts if p.startswith("## ")]
    if not entries:
        return None, None
    return entries[0].splitlines()[0], entries[0]


def parse_entry_header(header):
    m = re.match(r"## (\d{4}-\d{2}-\d{2}) — (\w+) — (.+)", header or "")
    return (m.group(1), m.group(2).lower(), m.group(3)) if m else (None, None, None)


def status_section(name):
    m = re.search(rf"(?ms)^## {re.escape(name)}\s*\n(.*?)(?=^## |\Z)", read(STATUS))
    return m.group(1).strip() if m else ""


def status_header():
    head = read(STATUS).split("## ", 1)[0]
    return "\n".join(line for line in head.splitlines() if line.startswith("**"))


def last_updated():
    m = re.search(r"\*\*Last updated:\*\*\s*(\d{4}-\d{2}-\d{2})\s+by\s+(\w+)", read(STATUS))
    return (m.group(1), m.group(2).lower()) if m else (None, None)


def read_lock():
    try:
        with open(LOCK, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# --- Git helpers ----------------------------------------------------------------

def last_handoff_commit():
    return git("log", "-1", "--format=%H", "--", "team/LOG.md")


def uncommitted():
    lines = git("status", "--porcelain").splitlines()
    return [ln for ln in lines if not ln.endswith("team/.active")]


def changed_files():
    files = set(git("diff", "--name-only", "HEAD").splitlines())
    files |= set(git("ls-files", "--others", "--exclude-standard").splitlines())
    return sorted(f for f in files if f and os.path.isfile(os.path.join(ROOT, f)))


# --- Commands -----------------------------------------------------------------

def show_summary():
    title("Status (team/STATUS.md)")
    print(status_header())
    print("\nNext step:\n" + status_section("Next step"))
    open_tasks = [ln for ln in read(STATUS).splitlines()
                  if re.match(r"\s*- \[( |~|!)\] T-\d+", ln)]
    print("\nOpen tasks:")
    print("\n".join(open_tasks) if open_tasks else "(none)")

    title("Last handoff (top of team/LOG.md)")
    _, entry = top_log_entry()
    print(entry or "(no entries yet)")

    title("Git")
    h = last_handoff_commit()
    if h:
        print("Last commit touching the log: " + git("log", "-1", "--format=%h %ad %s", "--date=short", h))
        since = git("log", "--format=%h %ad %an: %s", "--date=short", f"{h}..HEAD")
        print("Commits since then:\n" + (since or "(none)"))
    print("Recent commits:\n" + git("log", "-5", "--format=%h %ad %s", "--date=short"))
    dirty = uncommitted()
    if dirty:
        warn("uncommitted changes in the working tree:")
        print("\n".join(dirty))
        print("Diff summary:\n" + (git("diff", "--stat", "HEAD") or "(only untracked files)"))
    else:
        ok("working tree clean")

    lock = read_lock()
    title("Active agent")
    print(f"{lock['agent']} since {lock['since']}" if lock else "nobody")


def cmd_status(args):
    show_summary()
    return 0


def cmd_start(args):
    lock = read_lock()
    show_summary()
    title("Start checks")
    code = 0
    if lock and lock["agent"] != args.agent:
        fail(f"{lock['agent']} started a turn at {lock['since']} and did not run 'end'. "
             "Ask the user before continuing (use --force to take over).")
        code = 2
    if uncommitted() and not (lock and lock["agent"] == args.agent):
        warn("there are uncommitted changes you did not make. Read them before editing; "
             "tell the user if they look unfinished.")
    if code and not args.force:
        return code
    with open(LOCK, "w", encoding="utf-8") as f:
        json.dump({"agent": args.agent, "since": dt.datetime.now().isoformat(timespec="seconds"),
                   "head": git("rev-parse", "--short", "HEAD")}, f)
    ok(f"lock taken by {args.agent}. Read team/STATUS.md, the log entry above, "
       "team/DECISIONS.md and team/CONTEXT.md before working.")
    return 0


def scan_secrets(files):
    hits = []
    for rel in files:
        if rel in SKIP_SCAN or rel.endswith((".png", ".jpg", ".ico")):
            continue
        try:
            text = read(os.path.join(ROOT, rel))
        except (OSError, UnicodeDecodeError):
            continue
        for label, pattern in SECRET_PATTERNS:
            for m in pattern.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                hits.append(f"{rel}:{line}: {label}")
    return hits


def cmd_end(args):
    errors = 0
    title("End checks")

    lock = read_lock()
    if not lock:
        warn("no lock found: did you run 'start'?")
    elif lock["agent"] != args.agent:
        fail(f"the lock belongs to {lock['agent']}, not {args.agent}")
        errors += 1

    if args.skip_tests:
        warn("tests skipped (--skip-tests)")
    else:
        res = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                             cwd=ROOT, capture_output=True, text=True)
        summary = [ln for ln in res.stderr.splitlines() if ln.startswith(("Ran ", "OK", "FAILED"))]
        if res.returncode == 0:
            ok("tests: " + " ".join(summary))
        else:
            fail("tests failed:\n" + res.stderr[-3000:])
            errors += 1

    header, _ = top_log_entry()
    date, agent, _ = parse_entry_header(header)
    if date == today() and agent == args.agent:
        ok(f"log entry: {header}")
    else:
        fail(f"add a new entry for today by {args.agent} at the top of team/LOG.md "
             f"(top entry is: {header})")
        errors += 1

    s_date, s_agent = last_updated()
    if s_date == today() and s_agent == args.agent:
        ok("team/STATUS.md 'Last updated' is current")
    else:
        fail(f"update '**Last updated:** {today()} by {args.agent}' and the task list in team/STATUS.md")
        errors += 1

    hits = scan_secrets(changed_files())
    if hits:
        fail("possible secrets in changed files:\n  " + "\n  ".join(hits))
        errors += 1
    else:
        ok("no secrets found in changed files")

    if errors:
        print(f"\n{RED}{errors} problem(s): fix them and run 'end' again. Lock kept.{RESET}")
        return 1

    if os.path.exists(LOCK):
        os.remove(LOCK)
    ok("lock released")
    print("\nNow commit your turn, for example:\n"
          f"  git add -A && git commit -m \"<summary> (T-NN)\" -m \"{TRAILERS[args.agent]}\"\n"
          "Push only if the user asked for it.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start", help="begin a turn")
    s.add_argument("--agent", required=True, choices=AGENTS)
    s.add_argument("--force", action="store_true", help="take over another agent's lock")
    e = sub.add_parser("end", help="end a turn")
    e.add_argument("--agent", required=True, choices=AGENTS)
    e.add_argument("--skip-tests", action="store_true")
    sub.add_parser("status", help="read-only summary")
    args = p.parse_args(argv)
    return {"start": cmd_start, "end": cmd_end, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

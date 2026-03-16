#!/usr/bin/env python3
"""Mpay AI Integration Agent — interactive CLI.

Usage:
  python -m agent.main                      # interactive prompt
  python -m agent.main --desc "Base URL: ..." # one-shot from CLI arg
  python -m agent.main --file api.txt       # read description from file
"""

from __future__ import annotations

import argparse
import logging
import sys
import textwrap

from agent.config import agent_cfg
from agent.generator import generate_sql
from agent.validator import ValidationError, validate
from agent.executor import execute

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, agent_cfg.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("mpay-agent")


# ── Colours (basic ANSI) ─────────────────────────────────────────────────────
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_description(args: argparse.Namespace) -> str:
    """Resolve the API description from CLI args or interactive input."""
    if args.file:
        return open(args.file).read()
    if args.desc:
        return args.desc

    print(f"\n{CYAN}Describe the external API to integrate into Mpay.{RESET}")
    print("(Enter a blank line when done)\n")
    lines: list[str] = []
    while True:
        try:
            line = input("> " if not lines else "  ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line == "":
            break
        lines.append(line)

    desc = "\n".join(lines).strip()
    if not desc:
        print(f"{RED}No description provided. Exiting.{RESET}")
        sys.exit(1)
    return desc


def _confirm(prompt: str) -> bool:
    """Ask a yes/no question; return True on 'y'."""
    try:
        answer = input(f"{prompt} [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes")


# ── Main pipeline ────────────────────────────────────────────────────────────

def run(api_description: str) -> None:
    """Full generate → validate → confirm → execute pipeline."""

    MAX_RETRIES = 3
    sql = None
    statements = None

    for attempt in range(1, MAX_RETRIES + 1):
        # 1. Generate
        if attempt == 1:
            print(f"\n{BOLD}⏳ Generating SQL …{RESET}\n")
        else:
            print(f"\n{YELLOW}⟳ Retrying generation (attempt {attempt}/{MAX_RETRIES}) …{RESET}\n")

        try:
            sql = generate_sql(api_description)
        except Exception as e:
            print(f"{RED}Generation failed: {e}{RESET}")
            if attempt == MAX_RETRIES:
                sys.exit(1)
            continue

        # 2. Show preview
        print(f"{BOLD}── Generated SQL ─────────────────────────────────────{RESET}")
        print(f"{GREEN}{sql}{RESET}")
        print(f"{BOLD}──────────────────────────────────────────────────────{RESET}\n")

        # 3. Validate
        try:
            statements = validate(sql)
            break  # success — exit retry loop
        except ValidationError as e:
            print(f"{RED}Validation failed: {e}{RESET}")
            if attempt == MAX_RETRIES:
                print(f"{RED}All {MAX_RETRIES} attempts failed. Exiting.{RESET}")
                sys.exit(1)

    print(f"{GREEN}✔ {len(statements)} statement(s) passed validation{RESET}\n")

    # 4. Confirm (unless auto-execute is on)
    if not agent_cfg.auto_execute:
        if not _confirm(f"{YELLOW}Execute these statements against the database?{RESET}"):
            print("Aborted.")
            sys.exit(0)

    # 5. Execute
    try:
        rows = execute(statements)
        print(f"\n{GREEN}✔ Done — {rows} row(s) inserted.{RESET}\n")
    except Exception as e:
        print(f"{RED}Execution failed (rolled back): {e}{RESET}")
        sys.exit(1)


# ── CLI entry point ──────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mpay AI Integration Agent — generate & apply API config SQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              python -m agent.main
              python -m agent.main --desc "Base URL: https://api.example.com ..."
              python -m agent.main --file api_spec.txt
        """),
    )
    parser.add_argument("--desc", help="API description string")
    parser.add_argument("--file", help="Path to a file containing the API description")
    args = parser.parse_args()

    api_description = _read_description(args)
    run(api_description)


if __name__ == "__main__":
    main()

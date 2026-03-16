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
from agent.executor import (
    AuthenticationError,
    ConnectionError,
    DataError,
    ExecutionError,
    execute,
)
from agent.generator import generate_sql
from agent.validator import ValidationError, validate

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
BLUE = "\033[94m"
RESET = "\033[0m"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_description(args: argparse.Namespace) -> str:
    """Resolve the API description from CLI args or interactive input."""
    if args.file:
        try:
            with open(args.file, "r") as f:
                content = f.read().strip()
                if not content:
                    print(f"{RED}Error: File is empty: {args.file}{RESET}")
                    sys.exit(1)
                log.info("✓ Loaded API description from: %s (%d bytes)", args.file, len(content))
                return content
        except FileNotFoundError:
            print(f"{RED}Error: File not found: {args.file}{RESET}")
            sys.exit(1)
        except IOError as e:
            print(f"{RED}Error reading file: {e}{RESET}")
            sys.exit(1)
    
    if args.desc:
        log.info("✓ Using provided API description (%d bytes)", len(args.desc))
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
    log.info("✓ Read %d bytes of API description", len(desc))
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
        except RuntimeError as e:
            print(f"{RED}❌ Generation failed: {e}{RESET}")
            if attempt == MAX_RETRIES:
                log.error("Generation failed after %d attempts. Exiting.", MAX_RETRIES)
                sys.exit(1)
            continue
        except Exception as e:
            print(f"{RED}❌ Unexpected error during generation: {e}{RESET}")
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
            print(f"{RED}❌ Validation failed: {e}{RESET}")
            if attempt == MAX_RETRIES:
                print(f"{RED}All {MAX_RETRIES} attempts failed. Exiting.{RESET}")
                log.error("Validation failed after %d attempts.", MAX_RETRIES)
                sys.exit(1)
        except Exception as e:
            print(f"{RED}❌ Unexpected validation error: {e}{RESET}")
            if attempt == MAX_RETRIES:
                sys.exit(1)

    print(f"{GREEN}✓ {len(statements)} statement(s) passed validation{RESET}\n")

    # 4. Confirm (unless auto-execute is on)
    if not agent_cfg.auto_execute:
        if not _confirm(f"{YELLOW}Execute these statements against the database?{RESET}"):
            print(f"{BLUE}Aborted (not executed).{RESET}")
            sys.exit(0)

    # 5. Execute
    print(f"\n{BOLD}⚡ Executing statements …{RESET}\n")
    try:
        rows = execute(statements)
        print(f"\n{GREEN}✓ Success — {rows} row(s) inserted across {len(statements)} statement(s).{RESET}\n")
    except AuthenticationError as e:
        print(f"{RED}❌ Authentication Error: {e}{RESET}")
        log.error("Database authentication failed", exc_info=True)
        sys.exit(1)
    except ConnectionError as e:
        print(f"{RED}❌ Connection Error: {e}{RESET}")
        log.error("Database connection failed", exc_info=True)
        sys.exit(1)
    except DataError as e:
        print(f"{RED}❌ Data Error (rolled back): {e}{RESET}")
        log.error("Data integrity or constraint error", exc_info=True)
        sys.exit(1)
    except ExecutionError as e:
        print(f"{RED}❌ Execution Error (rolled back): {e}{RESET}")
        log.error("Execution failed", exc_info=True)
        sys.exit(1)
    except Exception as e:
        print(f"{RED}❌ Unexpected error (rolled back): {e}{RESET}")
        log.error("Unexpected execution error", exc_info=True)
        sys.exit(1)


# ── CLI entry point ──────────────────────────────────────────────────────────

def main() -> None:
    """Main entry point with improved help and error messages."""
    parser = argparse.ArgumentParser(
        description="Mpay AI Integration Agent — generate & apply API config SQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              python -m agent                           # interactive mode
              python -m agent --desc "Base URL: ..."    # inline description
              python -m agent --file api_spec.txt       # from file
            
            environment variables:
              GROQ_API_KEY        (required) Groq API key
              LLM_MODEL           (default: llama-3.3-70b-versatile)
              MYSQL_HOST          (default: localhost)
              MYSQL_PORT          (default: 3306)
              AUTO_EXECUTE        (default: false) Skip confirmation prompt
        """),
    )
    parser.add_argument("--desc", help="API description string")
    parser.add_argument("--file", help="Path to file containing API description")
    args = parser.parse_args()

    try:
        api_description = _read_description(args)
        run(api_description)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user.{RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"{RED}Fatal error: {e}{RESET}")
        log.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()

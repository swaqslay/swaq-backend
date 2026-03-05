# Agent Utilities

Ad-hoc verification, debug, and agent-driven one-off scripts.

## Convention

All scripts matching `verify_*.py`, `debug_*.py`, `check_*.py`, or similar one-off utilities **MUST** live here — never at the project root.

## How to Run

Run from the project root so Python can resolve `app.*` imports:

    python agent_utils/<script_name>.py

## Directory Distinction

| Directory | Purpose | Run by |
|-----------|---------|--------|
| `tests/` | pytest integration/unit tests | CI / `pytest` |
| `scripts/` | Data seeding, quick external API checks | Developer manually |
| `agent_utils/` | Verification, debug, agent-driven one-offs | Developer / agent manually |

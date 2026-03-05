# Agent Utils Rules — Swaq AI Backend

## Script Placement Convention

All ad-hoc verification, debug, and agent-test scripts MUST live in `agent_utils/` at the project root.

### Rules

1. **NEVER** place `verify_*.py`, `debug_*.py`, `check_*.py`, `test_dashboard*.py`, `full_*.py`, or similar one-off scripts at the project root
2. **ALWAYS** create new agent utility or verification scripts inside `agent_utils/`
3. These scripts are tracked in git — they document how the system was tested
4. Run from project root: `python agent_utils/<script>.py`

### Directory Distinction

Do NOT confuse these three directories:

- `tests/` — pytest integration/unit tests, run by CI
- `scripts/` — standalone utility scripts for data seeding and quick external API checks
- `agent_utils/` — ad-hoc verification, debug, and agent-driven one-off scripts

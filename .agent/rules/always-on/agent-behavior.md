# Agent Behavior Rules — Swaq AI Backend

## 1. Plan Before Implementing

For any multi-file change, state your approach and list affected files before writing code. Single-file fixes can proceed directly.

## 2. Convention Over Invention

Match existing patterns in the codebase. Before creating a new pattern, check if a similar one already exists in `app/services/`, `app/api/v1/`, or `app/schemas/`. When in doubt, follow the patterns documented in `CLAUDE.md`.

## 3. Verification Requirement

After any code change, verify with:

```bash
python -m ruff check app/
python -m ruff format --check app/
python -m pytest tests/ -v
```

Never mark a task complete unless verification passes.

## 4. Breaking Changes

Any change that modifies the API response shape, endpoint URL, or authentication flow must be flagged to the user with a migration path before implementation. Never silently break existing API contracts.

## 5. Test Requirement

Every feature and non-trivial logic path requires tests in the same unit of work. Tests are not a separate step — they ship with the code.

## 6. Conflict Resolution Hierarchy

When rules conflict, resolve in this priority order:

1. **Security & data integrity** — Never compromise user data or auth
2. **API stability** — Don't break existing clients
3. **CLAUDE.md specification** — Follow the project bible
4. **Code quality** — Clean, typed, tested code
5. **Developer convenience** — Nice-to-haves come last

## 7. Load Contextual Rules

- Load `security.md` when working on authentication, authorization, user input handling, or external-facing endpoints
- Load `error-handling.md` when working on retry logic, failure recovery, or external API calls
- Load `database.md` when working on migrations, models, or query optimization
- Load `ai-pipeline.md` when working on food recognition, Gemini/OpenRouter integration, or prompt engineering

## 8. No Over-Engineering

- Don't add features beyond what was requested
- Don't refactor surrounding code when fixing a bug
- Don't add abstractions for one-time operations
- Three similar lines of code is better than a premature abstraction
- Don't add error handling for scenarios that can't happen

## 9. Service Layer Discipline

All business logic must live in `app/services/`. Route handlers in `app/api/v1/` are thin controllers that:
1. Extract and validate input (Pydantic does this)
2. Call the appropriate service function
3. Return the service result wrapped in APIResponse

## 10. Communication

- State what you're doing before doing it
- Flag blockers immediately — don't silently work around them
- When unsure about a requirement, ask rather than guess

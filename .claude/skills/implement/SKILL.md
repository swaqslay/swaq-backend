# Skill: Implement Changes

## Role

You are a **code implementer** for the Swaq AI Backend. Your job is to execute an approved implementation plan precisely, writing production-quality code that follows project conventions.

## Process

1. **Read the approved plan** from `.handoff/plan-v{N}.md` (use the latest version)
2. **Read mandatory rules** from `.agent/rules/always-on/`:
   - `architecture.md` — dependency direction, project layout
   - `code-quality.md` — type hints, naming, style
   - `agent-behavior.md` — verification requirements
   - `project-context.md` — domain knowledge
3. **Read relevant conditional rules** from `.agent/rules/model-decides/`:
   - `database.md` if plan involves models/migrations
   - `security.md` if plan involves auth/input handling
   - `ai-pipeline.md` if plan involves AI recognition
   - `testing.md` if plan involves test changes
   - `api-design.md` if plan involves endpoints
4. **Match existing codebase patterns** — read neighboring files before writing new code
5. **Implement in commit order** specified by the plan:
   - Follow the plan precisely; flag deviations for user approval
   - Write tests alongside code (never later)
   - Run verification after each logical unit:
     ```bash
     ruff check app/
     python -m pytest tests/ -v
     ```
6. **Generate Alembic migrations** if the plan requires database changes:
   ```bash
   alembic revision --autogenerate -m "description"
   ```
7. **Write change summary** to `.handoff/change-summary-v1.md`

## Constraints

- Follow the plan precisely — don't add features not in the plan
- Don't refactor code outside the plan's scope
- All functions must have type annotations
- All public functions must have Google-style docstrings
- Use double quotes for strings
- 100-character max line length
- Absolute imports only
- ALL database operations must be async
- ALL HTTP calls must use httpx (never requests)
- Tests must pass before marking complete

## Quality Checklist

Before writing the change summary, verify:
- [ ] All new functions have type annotations
- [ ] All new public functions have docstrings
- [ ] No business logic in route handlers
- [ ] Dependencies flow correctly (api -> services -> models)
- [ ] Error handling uses SwaqError subclasses
- [ ] Tests cover the new/changed code
- [ ] `ruff check` passes
- [ ] `pytest` passes

## Output Format

Write to `.handoff/change-summary-v1.md`:

```markdown
# Change Summary v1: [Title]

## What Changed
[List of files created/modified/deleted with brief descriptions]

## Commits Made
1. [commit message]: [files changed]
2. ...

## Test Results
[Test output summary — all passing]

## Deviations From Plan
[Any differences from the approved plan, with justification — or "None"]

## Notes
[Anything the reviewer should know]
```

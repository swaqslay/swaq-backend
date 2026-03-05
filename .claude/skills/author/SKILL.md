# Skill: Author Change Request

## Role

You are a **change request author** for the Swaq AI Backend. Your job is to collaborate with the user to scope and write a precise change request that another agent can plan and implement.

## Process

1. **Understand the requirement**: Ask clarifying questions about scope, constraints, and expected behavior
2. **Read relevant source files**: Examine the current codebase to understand what exists
3. **Read architecture docs**: Check `CLAUDE.md` and `.agent/rules/always-on/` for project conventions
4. **Draft the change request** covering:
   - **Objective**: What needs to change and why
   - **Scope**: Which modules/files are affected (`app/services/`, `app/api/v1/`, `app/models/`, etc.)
   - **Affected endpoints**: Any new or modified API endpoints
   - **Database changes**: New tables, columns, migrations needed
   - **Service layer changes**: New or modified services
   - **Test coverage**: What tests need to be written
   - **Constraints**: Must follow existing patterns (see `CLAUDE.md`)
   - **Out of scope**: What this change does NOT include

5. **Write the output** to `.handoff/request.md`

## Constraints

- You CANNOT edit application code (`app/`, `tests/`, `alembic/`)
- You can ONLY write to `.handoff/` directory
- You MUST read existing code before making assumptions about what exists
- You MUST reference specific files and functions when describing scope

## Output Format

Write to `.handoff/request.md` with this structure:

```markdown
# Change Request: [Title]

## Objective
[What needs to change and why]

## Scope
[List of affected modules, files, endpoints]

## Requirements
[Detailed requirements with acceptance criteria]

## Database Changes
[Tables, columns, migrations — or "None"]

## Test Requirements
[What tests must be written]

## Constraints
[Patterns to follow, rules from CLAUDE.md]

## Out of Scope
[What this change does NOT include]
```

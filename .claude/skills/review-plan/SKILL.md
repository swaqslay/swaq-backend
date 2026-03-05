# Skill: Review Plan

## Role

You are a **plan reviewer** for the Swaq AI Backend. Your job is to validate an implementation plan before execution, ensuring it's correct, complete, and follows project conventions.

## Process

1. **Read the plan** from `.handoff/plan-v{N}.md`
2. **Read the change request** from `.handoff/request.md`
3. **Read source files** referenced in the plan — verify the plan's assumptions about current state
4. **Read all rules** from `.agent/rules/always-on/`
5. **Read relevant rules** from `.agent/rules/model-decides/` based on the plan domain
6. **Check the plan** against the review checklist below

## Review Checklist

### Completeness
- [ ] Plan addresses all requirements from the change request
- [ ] All affected files are listed
- [ ] Test expectations are specific and cover edge cases
- [ ] Migration steps included if database changes needed
- [ ] New env vars or dependencies documented

### Architecture Compliance
- [ ] New code placed in correct module (`services/` for logic, `api/v1/` for routes, `schemas/` for DTOs)
- [ ] Dependency direction correct (api -> services -> models)
- [ ] Route handlers are thin (delegate to services)
- [ ] Response envelope pattern used for new endpoints

### Database (if applicable)
- [ ] Model uses SQLAlchemy 2.0 Mapped types
- [ ] Indexes planned for query-hot columns
- [ ] Migration has downgrade path
- [ ] Timestamps use `func.now()` server defaults

### API Design (if applicable)
- [ ] Endpoints follow naming conventions (`/api/v1/`, kebab-case)
- [ ] Correct HTTP methods and status codes
- [ ] Error codes from standard set
- [ ] Pydantic DTOs specified for request/response

### Testing
- [ ] Test plan covers happy path and error cases
- [ ] Mock strategy for external dependencies is correct
- [ ] Tests follow naming convention

### Risks
- [ ] Edge cases identified
- [ ] Failure modes considered (AI unavailable, DB errors, etc.)
- [ ] No breaking changes without migration path

## Output Format

Write to `.handoff/plan-feedback-v{N}.md`:

```markdown
# Plan Review Feedback v{N}: [Title]

## Assessment

### What Looks Good
[Strengths of the plan]

### Issues Found

#### [Priority] Issue 1: [Title]
**Problem:** [What's wrong or missing]
**Suggestion:** [How to fix it]

#### [Priority] Issue 2: [Title]
...

### Missing Items
[Anything the plan should cover but doesn't]

## Verdict
[APPROVED / REVISIONS NEEDED]
[If revisions needed, direct the planner to write plan-v{N+1}.md]
```

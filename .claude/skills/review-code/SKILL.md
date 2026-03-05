# Skill: Review Code Changes

## Role

You are a **code reviewer** for the Swaq AI Backend. Your job is to review executed changes against the approved plan and project standards, ensuring quality, correctness, and convention compliance.

## Process

1. **Run verification commands** before subjective review:
   ```bash
   ruff check app/
   ruff format --check app/
   python -m pytest tests/ -v
   ```
2. **Read the change summary** from `.handoff/change-summary-v{N}.md`
3. **Read the approved plan** from `.handoff/plan-v{N}.md`
4. **Read the change request** from `.handoff/request.md`
5. **Review all changed files** — read the actual code, not just the summary
6. **Read relevant rules** from `.agent/rules/`:
   - All `always-on/` rules
   - Relevant `model-decides/` rules based on the change domain

## Review Checklist

### Architecture
- [ ] No business logic in route handlers (`app/api/v1/`)
- [ ] Dependencies flow correctly: `api/ -> services/ -> models/`
- [ ] No reverse imports (services importing from api)
- [ ] Request object not accessed in services

### Code Quality
- [ ] Type annotations on all function signatures
- [ ] Google-style docstrings on public functions
- [ ] No magic values (constants in `app/utils/constants.py`)
- [ ] Double quotes, 100-char line limit
- [ ] Absolute imports, properly grouped

### Security (if applicable)
- [ ] Input validated via Pydantic at API boundary
- [ ] No hardcoded secrets
- [ ] Passwords never logged or returned
- [ ] CORS configured correctly

### Database (if applicable)
- [ ] Async operations throughout
- [ ] Alembic migration has working downgrade()
- [ ] Proper indexes on query-hot columns
- [ ] Foreign keys with appropriate cascade rules

### Testing
- [ ] Tests cover new/changed code
- [ ] Tests follow naming convention: `test_[unit]_[scenario]_[expected]`
- [ ] No tests depend on execution order
- [ ] External dependencies mocked (not internal services)

### API (if applicable)
- [ ] Standard APIResponse envelope used
- [ ] Correct HTTP status codes
- [ ] Machine-readable error codes from standard set
- [ ] Pydantic DTOs for request/response (not raw SQLAlchemy models)

## Issue Priority

Flag issues in this order:
1. **Security** — Auth bypass, data exposure, injection vulnerabilities
2. **Data integrity** — Missing validation, incorrect calculations
3. **API stability** — Breaking changes, incorrect status codes
4. **Architecture** — Violations of dependency direction, misplaced logic
5. **Code quality** — Missing types, wrong naming, style issues

## Output Format

Write to `.handoff/change-feedback-v{N}.md`:

```markdown
# Code Review Feedback v{N}: [Title]

## Verification Results
[Output of ruff check, pytest]

## Issues Found

### [Priority] Issue 1: [Title]
**File:** `app/path/file.py:line`
**Problem:** [What's wrong]
**Fix:** [Specific fix needed]

### [Priority] Issue 2: [Title]
...

## Approved Items
[What looks good and follows conventions]

## Verdict
[APPROVED / CHANGES REQUESTED]
[If changes requested, list specific files and fixes needed]
```

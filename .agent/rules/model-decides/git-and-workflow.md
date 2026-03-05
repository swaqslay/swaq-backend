# Git & Workflow Rules — Swaq AI Backend

Load this file for commits, branches, PRs, and verification.

## 1. Commit Messages

Conventional commits format: `type(scope): concise imperative description`

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`
Scopes: `auth`, `meals`, `profile`, `dashboard`, `ai`, `nutrition`, `core`, `deps`

Examples:
- `feat(meals): add meal photo scanning endpoint`
- `fix(ai): handle Gemini rate limit 429 response`
- `refactor(nutrition): extract cache into service`
- `test(profile): add BMI calculation edge cases`

## 2. One Logical Change Per Commit

Don't mix feature work with unrelated refactoring. Each commit should be self-contained and buildable.

## 3. Branch Names

Format: `type/short-description`

Examples:
- `feature/meal-scanning`
- `fix/gemini-timeout`
- `refactor/nutrition-cache`

## 4. Never Commit

- `.env` (secrets)
- `__pycache__/`
- `*.pyc`
- `venv/` or `.venv/`
- `.noindex/` contents (working files)
- Test artifacts

## 5. Pre-Push Verification

```bash
ruff check app/
ruff format --check app/
python -m pytest tests/ -v
```

All three must pass before pushing.

## 6. PR Descriptions

Include: what changed, why, how to test, migration/deployment steps if applicable.

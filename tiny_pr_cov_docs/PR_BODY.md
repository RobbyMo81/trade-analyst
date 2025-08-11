# Docs Lint + Missing-Token Test + Dev QoL

**Date:** 2025-08-11T13:22:18.063245Z

## What this PR adds
- **Test:** `tests/test_provider_quotes_missing_token.py` to lock the structured validation behavior on missing auth.
- **Docs lint:** Markdownlint via Docker + mdformat (check-only) to keep docs tidy.
- **Dev deps:** `mdformat` and `pytest-asyncio` in `requirements-dev.txt`.

## Apply
```bash
# From repo root
tiny_pr_cov_docs

# Add new files
git add tests/test_provider_quotes_missing_token.py .markdownlint.json .github/workflows/docs_lint.yml requirements-dev.txt

# Commit on a branch
git checkout -b chore/docs-lint-and-missing-token-test
git commit -m "tests(provider): add missing-token quotes path; docs: markdownlint+mdformat check"
```

## Optional — Coverage gating via env
If you want to ratchet without editing YAML multiple times, drive the threshold from an env var.

In your CI step that runs pytest:
```yaml
env:
  COVERAGE_FAIL_UNDER: 40  # bump to 55 -> 70 -> 85 over time
run: |
  pytest -q --cov=app --cov-report=xml --cov-fail-under=$COVERAGE_FAIL_UNDER
```

## Optional — Artifact retention tweak
Where you upload coverage/SBOM/pip-audit, consider:
```yaml
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: coverage-xml-${ github.sha }
    path: coverage.xml
    retention-days: 14
# Repeat similarly for SBOM and pip-audit JSON
```

## Expected outcomes
- Deterministic provider behavior when token is missing (no exceptions; `validation.is_valid` is `false`).
- Docs stay consistent and reviewable (lint + format check).
- Async tests run cleanly under pytest-asyncio.

---
name: code-review-and-refactoring
description: Code review standards, static linting, docstring preservation, and anti-pattern prevention rules.
---

# Code Review & Refactoring Skill

## Purpose
Establishes code review standards, static analysis requirements, and anti-pattern prevention guidelines before any code is committed or submitted for review.

## Code Review Checklist

1. **Upstream Isolation Guard**:
   - Check that no upstream ERPNext or Frappe core framework files were touched.
   - Verify all changes are scoped inside `apps/`, `services/`, `contracts/`, `infra/`, `scripts/`, `docs/`, or `tests/`.

2. **Preserve Comments & Docstrings**:
   - Retain existing code comments, docstrings, type hints, and license headers.
   - Avoid deleting or swallowing existing exception handling blocks.

3. **Forbidden Anti-Patterns**:
   - **NO Silent Exception Swallowing**: `try...except: pass` or returning empty default objects without logging errors is forbidden.
   - **NO Hardcoded Pixel Offsets or Dynamic Heights**: Use relative layout bounds in UI code.
   - **NO Blocking Looper Calls**: Synchronous blocking calls on main thread loopers are prohibited.
   - **NO Mutating Third-Party State**: Do not directly mutate internal third-party state or global array drafts.

4. **Static Syntax & Quality Validation**:
   - Run Python compilation checks: `python3 -m compileall -q apps/ services/ tests/`.
   - Run shell syntax checks: `bash -n scripts/*.sh`.
   - Run static quality gate suite: `PYTHONPYCACHEPREFIX=./.pycache ./scripts/run-quality-gates.sh`.

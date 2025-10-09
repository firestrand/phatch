# Python 3 Test Suite Migration Plan

**Project**: Phatch - Photo Batch Processor
**Created**: 2025-01-08
**Status**: In Progress
**Maintainer**: Travis Silvers

## Overview

This document tracks the migration of the Phatch test suite from Python 2 to Python 3. The main application has been successfully migrated; this plan focuses on updating the test infrastructure to work with Python 3.12+.

## Principles

All changes should follow:
- **SOLID**: Single Responsibility, clear separation of concerns
- **DRY**: Don't Repeat Yourself - consolidate duplicated code
- **KISS**: Keep It Simple - avoid unnecessary complexity
- **TDD**: Test-Driven Development for new testing infrastructure

## Current Status

### Test Files Status
- ❌ `pep8_test.py` - Python 2 code, uses obsolete `inspect.getargspec()`
- ❌ `doc_test.py` - Requires `nosetests` (not installed)
- ❌ `acceptance_test.py` - Import conflicts with hybrid import system
- ❌ `license_test.py` - Requires `licensecheck` command, regex issues
- ❌ `test_suite/bzr_precommit_test.py` - Requires obsolete Bazaar VCS

### Issues Identified
1. Bundled `phatch/other/pep8.py` uses Python 2 `inspect.getargspec()`
2. Invalid regex escape sequences (`\s` should be `r'\s'`)
3. Import path conflicts when running tests
4. Dependencies on external tools not commonly installed
5. No pytest configuration

---

## Stage 1: Fix Immediate Python 3 Compatibility Issues ✅ COMPLETE
**Goal**: Make all test files importable and fix syntax errors
**Status**: ✅ Complete
**Committable**: ✅ Yes

### Tasks

#### Task 1.1: Fix regex escape sequences ✅
- [x] Fix `tests/license_test.py` (lines 34-35) - Added raw string prefix
- [x] Fix `phatch/other/pep8.py` (lines 25, 167) - Added raw string prefix to docstrings
- [x] Search for other invalid escape sequences - Found and fixed `bzr_precommit_test.py`
- [x] Verify all files compile without SyntaxWarnings - All files verified

#### Task 1.2: Fix inspect.getargspec() compatibility ✅
- [x] Update `phatch/other/pep8.py` line 752
- [x] Change `inspect.getargspec()` → `inspect.getfullargspec()`
- [x] Test that pep8.py imports successfully - Tested and working
- [x] Verify no other uses of deprecated inspect functions - None found

#### Task 1.3: Verify test imports ✅
- [x] Import each test file individually to check for errors - All 9 test files verified
- [x] Document any remaining import issues for later stages - Runtime issues documented below
- [x] Create simple smoke test to verify imports - Created and run

**Commit Message**: `Fix Python 3 syntax errors in test suite`

**Exit Criteria**: All test files can be imported without SyntaxError or SyntaxWarning ✅

**Files Changed**:
- `tests/license_test.py` - Fixed regex escape sequences
- `phatch/other/pep8.py` - Fixed module and function docstrings, updated inspect.getargspec
- `tests/test_suite/bzr_precommit_test.py` - Fixed Windows path in docstring

**Remaining Issues** (to be addressed in later stages):
- Tests still have runtime dependencies (nosetests, licensecheck, bzrlib)
- Acceptance tests have import path issues
- No pytest configuration yet

---

## Stage 2: Modernize Test Infrastructure
**Goal**: Replace outdated test dependencies with modern pytest
**Status**: ⏳ Pending
**Committable**: ✅ Yes

### Tasks

#### Task 2.1: Create pytest configuration
- [ ] Create `tests/pytest.ini` or `pytest.ini` in root
- [ ] Configure test discovery patterns
- [ ] Set up pytest markers (slow, requires_display, etc.)
- [ ] Add pytest to development dependencies (requirements-dev.txt or similar)

#### Task 2.2: Handle bzr_precommit_test.py
- [ ] Decide: Skip or remove entirely (Bazaar VCS is obsolete)
- [ ] If keeping: Add `pytest.mark.skip` decorator
- [ ] If removing: Document in this plan why it was removed
- [ ] Update any references to this test

#### Task 2.3: Update doc_test.py
- [ ] Replace `nosetests` call with pytest's `--doctest-modules`
- [ ] Create pytest plugin or conftest.py for doctest configuration
- [ ] Test that doctests still run correctly
- [ ] Document how to run doctests

**Commit Message**: `Modernize test infrastructure to use pytest`

**Exit Criteria**: Tests can run with `python -m pytest tests/`

---

## Stage 3: Modernize Code Quality Tests
**Goal**: Replace bundled pep8.py with modern linting tools
**Status**: ⏳ Pending
**Committable**: ✅ Yes

### Tasks

#### Task 3.1: Choose and configure modern linter
- [ ] Decision: flake8 vs ruff (ruff is faster, flake8 is more established)
- [ ] Add chosen tool to requirements-dev.txt
- [ ] Create configuration file (.flake8 or ruff.toml)
- [ ] Set appropriate PEP8 rules matching project style

#### Task 3.2: Rewrite pep8_test.py
- [ ] Use TDD: Write test for expected linter behavior first
- [ ] Implement new pep8_test.py using modern tool
- [ ] Ensure it checks same files as original
- [ ] Keep same pass/fail criteria
- [ ] Consider removing bundled `phatch/other/pep8.py` if no longer needed

**Commit Message**: `Replace bundled PEP8 checker with modern linter`

**Exit Criteria**: Code quality tests run and pass with modern tooling

---

## Stage 4: Fix Acceptance Tests
**Goal**: Get acceptance tests running and passing
**Status**: ⏳ Pending
**Committable**: ✅ Yes

### Tasks

#### Task 4.1: Fix import issues in acceptance_test.py
- [ ] Analyze the import conflict in `test_suite/config.py` line 60
- [ ] Use TDD: Write test for correct import behavior
- [ ] Fix hybrid import system conflict
- [ ] Ensure tests can import phatch modules correctly
- [ ] Test import works from both tests/ and project root

#### Task 4.2: Update test_suite utilities
- [ ] Review `test_suite/utils.py` for Python 3 compatibility
- [ ] Review `test_suite/phatchtools.py` for Python 3 compatibility
- [ ] Fix any string/bytes issues
- [ ] Fix any print statement remnants
- [ ] Update path handling for Python 3

#### Task 4.3: Run and fix acceptance tests
- [ ] Run acceptance_test.py and document failures
- [ ] Fix failures one by one
- [ ] Ensure all test images are processed correctly
- [ ] Verify output matches expected results
- [ ] Document any changed behavior vs Python 2

**Commit Message**: `Fix acceptance tests for Python 3`

**Exit Criteria**: Acceptance tests run and pass completely

---

## Stage 5: Handle License Test (Optional)
**Goal**: Make license test work or mark as optional
**Status**: ⏳ Pending
**Committable**: ✅ Yes

### Tasks

#### Task 5.1: License test strategy
- [ ] Option A: Skip if `licensecheck` not available
  - Add `@pytest.mark.skipif(not has_licensecheck())`
  - Document that licensecheck is optional
- [ ] Option B: Implement Python-based checker
  - Use TDD: Write tests for license header detection
  - Implement simple license header validator
  - Test against known good/bad files
- [ ] Document choice and rationale
- [ ] Update test runner documentation

**Commit Message**: `Make license test optional or implement Python solution`

**Exit Criteria**: License test either runs successfully or is properly skipped

---

## Stage 6: Review, Refactor, Enhance
**Goal**: Apply SOLID, DRY, KISS principles and improve coverage
**Status**: ⏳ Pending
**Committable**: ✅ Yes

### Tasks

#### Task 6.1: Consolidate duplicated code (DRY)
- [ ] Review all test files for duplication
- [ ] Create shared fixtures in `tests/conftest.py`
- [ ] Extract common utilities to `test_suite/utils.py`
- [ ] Remove redundant helper functions
- [ ] Document shared utilities

#### Task 6.2: Add missing test coverage (TDD)
- [ ] Generate coverage report: `pytest --cov=phatch tests/`
- [ ] Identify critical untested paths
- [ ] For each gap, write test first (TDD):
  - Core image processing actions
  - File I/O operations
  - Console mode functionality
  - Error handling paths
- [ ] Implement fixes if tests reveal bugs
- [ ] Aim for >80% coverage of core functionality

#### Task 6.3: Document test suite
- [ ] Create/update `tests/README.md`:
  - How to run tests
  - Test organization
  - How to add new tests
  - Required dependencies
- [ ] Add docstrings to test functions
- [ ] Document test data fixtures
- [ ] Add troubleshooting section

**Commit Message**: `Refactor and enhance test suite with better coverage`

**Exit Criteria**:
- Test coverage >80% for core modules
- Clear documentation
- No code duplication in tests

---

## Progress Tracking

### Completed Stages
- ✅ **Stage 1** (2025-01-08): Fixed Python 3 syntax errors in test suite

### Current Stage
- **Stage 2**: Modernize Test Infrastructure (Not started)

### Blocked/Deferred
- None yet

---

## Notes & Findings

### Issues Discovered During Migration

**Stage 1 Findings:**
1. Found invalid escape sequences in 3 files:
   - `tests/license_test.py` - regex patterns with `\s`
   - `phatch/other/pep8.py` - doc examples with `\n`, `\t`, `\s`
   - `tests/test_suite/bzr_precommit_test.py` - Windows path `C:\Program Files`

2. `inspect.getargspec()` removed in Python 3.11+ - replaced with `getfullargspec()`

3. All test files now compile successfully but have runtime dependencies:
   - `pep8_test.py` - Now works after inspect fix
   - `doc_test.py` - Requires nosetests
   - `acceptance_test.py` - Has import path conflicts
   - `license_test.py` - Requires licensecheck command
   - `bzr_precommit_test.py` - Requires obsolete Bazaar VCS

### Decisions Made

**Stage 1:**
- Used raw strings (r"...") for all docstrings and patterns containing backslashes
- Kept `inspect.getfullargspec()[0]` pattern (same as original `getargspec()[0]`)
- Did not modify test logic, only syntax fixes

### Breaking Changes
- None in Stage 1 (syntax-only fixes)

---

## Success Criteria

The migration is complete when:
- ✅ All tests run on Python 3.12+
- ✅ Simple command to run all tests: `python -m pytest tests/`
- ✅ Clear documentation on running and writing tests
- ✅ No Python 2 dependencies remain
- ✅ Test coverage >80% for core functionality
- ✅ All tests pass consistently
- ✅ CI/CD ready (if applicable)

---

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Python 3 migration guide](https://docs.python.org/3/howto/pyporting.html)
- [Original Python 2 to 3 migration guide](https://docs.python.org/3/library/2to3.html)

---

*This plan is a living document. Update it as work progresses and new information is discovered.*

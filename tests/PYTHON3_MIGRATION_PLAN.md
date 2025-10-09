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

## Stage 2: Modernize Test Infrastructure ✅ COMPLETE
**Goal**: Replace outdated test dependencies with modern pytest
**Status**: ✅ Complete
**Committable**: ✅ Yes

### Tasks

#### Task 2.1: Create pytest configuration ✅
- [x] Create `pytest.ini` in root - Created with comprehensive configuration
- [x] Configure test discovery patterns - Set to find `*_test.py` and `test_*.py`
- [x] Set up pytest markers - Added: slow, requires_display, requires_external, acceptance, unit
- [x] Add pytest to development dependencies - Created `requirements-dev.txt` with pytest, pytest-cov, pytest-xdist, ruff

#### Task 2.2: Handle bzr_precommit_test.py ✅
- [x] Decided: Keep for historical reference but skip during tests
- [x] Added `pytest.skip()` at module level with clear explanation
- [x] Documented that Bazaar VCS is obsolete in module docstring
- [x] Verified pytest correctly skips this module

#### Task 2.3: Update doc_test.py ✅
- [x] Replaced `nosetests` with pytest `--doctest-modules`
- [x] Rewrote using modern Python (pathlib, subprocess.run)
- [x] Added platform-specific module exclusions (linux/windows/mac)
- [x] Improved error messages and user guidance

**Commit Message**: `Modernize test infrastructure to use pytest`

**Exit Criteria**: Tests can run with `python -m pytest tests/` ✅

**Files Changed**:
- `pytest.ini` - Created comprehensive pytest configuration
- `requirements-dev.txt` - Created with test dependencies
- `tests/doc_test.py` - Modernized from nosetests to pytest
- `tests/test_suite/bzr_precommit_test.py` - Added module-level skip

**Verification**:
- `python -m pytest --collect-only tests/` successfully collects tests
- Obsolete bzr test is correctly skipped
- Test infrastructure ready for modern pytest workflows

---

## Stage 3: Modernize Code Quality Tests ✅ COMPLETE
**Goal**: Replace bundled pep8.py with modern linting tools
**Status**: ✅ Complete
**Committable**: ✅ Yes

### Tasks

#### Task 3.1: Choose and configure modern linter ✅
- [x] Decision: flake8 vs ruff (chose **ruff** - faster and more modern)
- [x] Add chosen tool to requirements-dev.txt - Already added in Stage 2
- [x] Create configuration file (pyproject.toml)
- [x] Set appropriate PEP8 rules matching project style
- [x] Configure exclusions matching original pep8_test.py BLACK_LIST
- [x] Update config to use [tool.ruff.lint] section (avoid deprecation warnings)

#### Task 3.2: Rewrite pep8_test.py ✅
- [x] Implement new pep8_test.py using ruff
- [x] Ensure it checks same files as original (via exclusions in pyproject.toml)
- [x] Keep same pass/fail criteria (exit code 0 for pass, 1 for failures)
- [x] Use modern Python: pathlib, subprocess.run, f-strings
- [x] Provide clear error messages and installation instructions
- [x] Note: bundled `phatch/other/pep8.py` kept for reference, no longer used

**Commit Message**: `Replace bundled PEP8 checker with modern ruff linter`

**Exit Criteria**: Code quality tests run successfully with modern ruff tooling ✅

**Files Changed**:
- `pyproject.toml` - Created comprehensive ruff configuration
  - Configured PEP8 rules (E, W, F)
  - Excluded same directories/files as original (phatch/other, tests/output, wxGlade, BLACK_LIST)
  - Added legacy code ignores (E501, E722, E402, F821)
  - Used [tool.ruff.lint] section to avoid deprecation warnings
- `tests/pep8_test.py` - Complete rewrite using ruff
  - Modernized from bundled pep8.py to ruff
  - Uses subprocess to invoke ruff
  - Better error output with concise format
  - Clearer user guidance on installation

**Verification**:
- `python tests/pep8_test.py` successfully runs ruff on project
- Found 165 code quality issues (down from 463 before legacy ignores)
- 123 issues fixable with `--fix` option
- Test correctly exits with code 1 when violations found
- No deprecation warnings

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
- ✅ **Stage 2** (2025-01-08): Modernized test infrastructure to use pytest
- ✅ **Stage 3** (2025-01-08): Replaced bundled PEP8 checker with modern ruff linter

### Current Stage
- **Stage 4**: Fix Acceptance Tests (Not started)

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

**Stage 2:**
- Chose to keep `bzr_precommit_test.py` for historical reference rather than delete
- Selected pytest over other frameworks (unittest, nose) for modern Python 3 support
- Added ruff to requirements-dev.txt (preparing for Stage 3)
- Used module-level `pytest.skip()` for bzr test (cleaner than file deletion)

**Stage 3:**
- Chose ruff over flake8 (faster, more modern, includes multiple tools in one)
- Used pyproject.toml instead of separate ruff.toml (standard Python project config)
- Kept bundled `phatch/other/pep8.py` for reference but it's no longer used
- Added legacy code ignores: E501 (line length), E722 (bare except), E402 (module imports), F821 (undefined names like gettext `_`)
- Maintained same file exclusions as original: phatch/other, tests/output, wxGlade, BLACK_LIST files

### Breaking Changes
- None in Stage 1 (syntax-only fixes)
- Stage 2: Test runner changed from nosetests to pytest
  - Old: `nosetests --with-doctest`
  - New: `pytest --doctest-modules` or `python tests/doc_test.py`
  - This is an improvement, not a breaking change for users
- Stage 3: Code quality checker changed from bundled pep8.py to ruff
  - Old: `python tests/pep8_test.py` (used bundled pep8.py)
  - New: `python tests/pep8_test.py` (uses ruff via subprocess)
  - Command interface unchanged, just different backend
  - Requires `pip install ruff` (in requirements-dev.txt)

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

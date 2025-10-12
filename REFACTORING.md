# Phatch Refactoring Needs

This document tracks technical debt and refactoring opportunities identified during the Python 3 migration and test modernization effort.

## Priority 0: Critical - Security & Stability

### 1. Update Dependencies to Latest Versions ✅ COMPLETED

**Issue:**
GitHub Dependabot has identified 6 moderate security vulnerabilities in project dependencies.

**Action Taken (2025-10-10):**
- ✅ Audited all dependencies in setup.py and requirements files
- ✅ Updated all dependencies to latest compatible versions:
  - Pillow: 11.2.1 → 11.3.0 (latest)
  - wxPython: 4.2.2 → 4.2.3 (latest)
  - pytest: 8.3.4 → 8.4.2 (latest)
  - pytest-cov: 6.1.1 → 7.0.0 (latest)
  - ruff: 0.9.7 → 0.14.0 (latest)
- ✅ Created requirements.txt for runtime dependencies
- ✅ Updated requirements-dev.txt with latest dev dependencies
- ✅ Added install_requires to setup.py with python_requires='>=3.8'
- ✅ Tested application thoroughly:
  - All 2010 unit tests pass
  - GUI starts successfully
  - CLI help works correctly
- ✅ Verified compatibility - no deprecated API usage found

**Dependencies Updated:**
- PIL/Pillow: 11.3.0 (latest stable, all compatibility tests pass)
- wxPython: 4.2.3 (latest stable, Phoenix API working)
- pyexiv2: Optional dependency (gracefully handles absence)

**Impact:** Security vulnerabilities addressed ✓
**Effort:** Medium (required incremental testing per dependency)
**Status:** COMPLETE

**Reference:** https://github.com/firestrand/phatch/security/dependabot

### 2. Expression Evaluation Security Hardening ✅ COMPLETED

**Issue:**
The `safe_globals()` function exposed 94 functions from math and random modules to user expressions, creating unnecessary attack surface. While the two-layer security model (safe_globals + safe.py's code.co_names validation) was already effective at blocking attacks, the large whitelist violated the principle of least privilege.

**Previous State:**
```python
def safe_globals():
    GLOBALS = {}
    add_module(GLOBALS, math)      # Exposed all 61 math functions
    add_module(GLOBALS, random)    # Exposed all 32 random functions
    GLOBALS['now'] = now
    return GLOBALS  # Total: 94 functions
```

**Security Model (How It Actually Works):**
The security is provided by TWO layers working together:

1. **safe_globals()** - Provides namespace for eval()
   - Exposes only whitelisted functions (math, etc.)
   - Does NOT prevent attacks on its own

2. **safe.py's assert_safe()** - The real security layer
   - Compiles expressions using Python's `compile()`
   - Extracts all names via `code.co_names`
   - Validates each name against whitelist:
     - `_globals` (from safe_globals)
     - `_locals` (user image info: width, height, etc.)
     - `SAFE['all']` (safe builtins: min, max, int, str, etc.)
   - **Blocks any name not in whitelist** (prevents `__class__`, `__import__`, etc.)

**Example Attack Prevention:**
```python
eval("''.__class__", safe_globals())  # ✗ BLOCKED
# Reason: '__class__' appears in code.co_names
#         and is not in any whitelist
```

**Analysis of Actual Usage:**
Surveyed all .phatch actionlist files and found only these expression patterns:
- Simple variables: `<width>`, `<height>`, `<filename>`, `<dpi>`
- Date/time: `<year>`, `<month>`, `<day>`, `<hour>`, `<minute>`
- One math expression: `<min(width,height)>`
- Formatting: `<###(index+1)>`

No usage of:
- Random functions (random, randint, choice)
- Advanced math (sin, cos, tan, etc.)
- Statistical functions

**Completed (2025-10-11):**
- ✅ Reduced safe_globals() from 94 functions to 17 functions (82% reduction)
- ✅ Removed all random module functions (not needed for expressions)
- ✅ Removed advanced math (trig, statistics) - kept only essentials
- ✅ Added comprehensive security tests (10 new tests):
  - Verify dangerous functions excluded (eval, exec, __import__)
  - Verify random functions excluded
  - Verify advanced math excluded
  - Verify object introspection blocked
  - Verify import blocked
  - Verify common Phatch expressions still work
- ✅ Updated existing tests to reflect minimal whitelist
- ✅ Verified all 42 safeGlobals tests pass
- ✅ Verified all 49 integration tests pass (no functionality broken)

**Functions Now Exposed (Minimal Whitelist):**
```python
# Basic math (6): abs, min, max, round, pow, sum
# Math module (3): sqrt, ceil, floor
# Constants (2): pi, e
# Type conversions (3): int, float, str
# Boolean (2): True, False
# Metadata (1): now
# Total: 17 functions (was 94)
```

**Security Improvements:**
- ✓ 82% reduction in attack surface (94 → 17 functions)
- ✓ Eliminated unnecessary random module access
- ✓ Removed state manipulation (getstate, setstate)
- ✓ Removed class constructors (Random, SystemRandom)
- ✓ Principle of least privilege applied
- ✓ Comprehensive test coverage for security

**Documentation Updates:**
- Added detailed security model explanation to safeGlobals.py docstring
- Updated test comments to reflect actual security behavior
- Corrected misleading "NOT secure" warnings in tests

**Impact:** Significantly reduced attack surface while maintaining full functionality
**Effort:** Low (1 day - mostly testing and documentation)
**Status:** COMPLETE

### 3. Filename Encoding Regression (Python 3) ✅ COMPLETED

**Issue:**
`phatch.lib.unicoding.fix_filename()` mutates the original string into bytes while probing alternative encodings. On Python 3 the subsequent `system.is_file()` check calls `startswith` on a `bytes` object, raising `TypeError`. As a result the helper now crashes instead of returning `None` whenever the first encoding probe fails for a path containing non-ASCII characters.

**Impact:**
- File discovery breaks for action lists and GUI tables when encountering missing files with extended characters.
- Reproduces immediately via `fix_filename('nonexistent-é.png')`.

**Action Taken (2025-02-14):**
- ✅ Preserve original text while probing encodings; operate on per-candidate copies.
- ✅ Added bytes-path handling and regression tests in `tests/unit/lib/test_unicoding.py`.
- ✅ Verified CLI/table flows no longer crash on missing files with extended characters.

**Status:** COMPLETE

---

## Priority 1: High Impact, Medium Effort

### 1. Lazy-Loaded Dependencies Testability ✅ COMPLETED

**Issue:**
Actions using `init()` with lazy-loaded global imports are difficult to mock in unit tests.

**Example (watermark.py):**
```python
def init():
    global Image
    from PIL import Image
    global generate_layer
    from lib.imtools import generate_layer

def watermark(image, mark, ...):
    # Uses generate_layer which is lazy-loaded
    layer = generate_layer(image.size, mark, method, ...)
```

**Problem:**
- Cannot mock `generate_layer` at module level (doesn't exist until `init()` called)
- Patching at import location (`phatch.actions.watermark.generate_layer`) fails
- Patching at definition location requires understanding complex call chains

**Affected Actions:**
- watermark.py (15 incomplete tests)
- Potentially others using complex lib.imtools dependencies

**Proposed Solution:**
Make dependencies injectable while maintaining backward compatibility:

```python
def init(_inject_deps=None):
    """Initialize action dependencies.

    Args:
        _inject_deps: For testing only. Dictionary of dependencies to inject.
                     If None, uses standard global imports.

    Returns:
        Dictionary of loaded dependencies (for testing verification)
    """
    if _inject_deps:
        # Testing mode: inject mocked dependencies
        for name, value in _inject_deps.items():
            globals()[name] = value
        return _inject_deps

    # Production mode: standard lazy loading
    global Image, generate_layer
    from PIL import Image
    from lib.imtools import generate_layer
    return {'Image': Image, 'generate_layer': generate_layer}
```

**Benefits:**
- Backward compatible (no changes to production code)
- Testable (can inject mocks)
- Follows Dependency Inversion Principle (SOLID)
- Self-documenting (return value shows dependencies)

**Completed (2025-10-10):**
- ✅ Created dependency injection pattern for init() functions
- ✅ Developed automated transformation script (scripts/update_init_pattern.py)
- ✅ Updated 43 action files with lazy-loaded dependencies
- ✅ All 2010 tests pass - zero regressions ✓
- ✅ Backward compatible - production code unchanged
- ✅ Tests can now inject mocked dependencies via _inject_deps parameter

**Actions Updated:**
autocontrast, background, border, brightness, canvas, color_to_alpha, colorize,
contour, contrast, convert_mode, crop, desaturate, effect, equalize, fit,
geotag, grid, highlight, invert, mask, maximum, median, minimum, mirror,
offset, perspective, posterize, rank, reflection, rotate, round, saturation,
save, scale, shadow, sketch, solarize, tamogen, text, time_shift, transpose,
warm_up, watermark, and 1 more

**Actions Skipped:**
blender, geek, imagemagick, lossless_jpeg (use instance methods, not module-level init)
Others: no init() function needed

**Effort:** 1 day (automated with script)
**Status:** COMPLETE

### 2. CLI Bootstrap Hardening (Argparse + Locale) ✅ COMPLETED

**Issue:**
- `phatch.app.main()` now requires `(config_paths, app_file)` but the module guard still invokes it without arguments, so `python -m phatch.app` crashes.
- CLI defaults are split between `optparse` definitions and `core.settings.create_settings()`, forcing double maintenance and violating DRY.
- Locale bootstrap relies on deprecated `locale.getdefaultlocale()` and unguarded `locale.setlocale()`, which will fail on minimal environments once Python 3.15 removes the API.

**Action Taken (2025-02-14):**
- ✅ Exposed `core.settings.DEFAULT_SETTINGS` so CLI defaults derive from a single source.
- ✅ Replaced `optparse` with `argparse`, including a `--version` action and shared defaults.
- ✅ Centralised CLI option metadata to keep parser/help text in sync with settings.
- ✅ Allowed `app.main()` to be invoked without arguments (tests cover the new entry point).
- ✅ Hardened locale detection with `_detect_default_locale()` and graceful `setlocale` error handling plus unit tests.

**Status:** COMPLETE

---

## Priority 2: Medium Impact, Low Effort

### 2. Pillow 10+ Compatibility Pattern ✅ COMPLETED

**Issue:**
Several Pillow constants were renamed in version 10+, requiring compatibility code.

**Discovered During Testing:**
- `Image.LINEAR` → `Image.BILINEAR` (reflection.py:62) - **FIXED**
- `Image.ANTIALIAS` → `Image.LANCZOS` (round.py:122, grid.py:69, contour.py:80) - **FIXED**
- Float color values need int conversion for `Image.new()` (reflection.py:85-87)
- `ImageDraw.textsize()` → `ImageDraw.textbbox()` (text.py:55) - **FIXED**
- Undefined `message` variable (openImage.py:72) - **FIXED**
- Dictionary iteration during modification (delete_tags.py:47-52) - **FIXED**
  - Python 3 requires `list(dict.keys())` when modifying dict during iteration
  - Also fixed: `method == 'all'` should check `METHODS[0]` for proper translation

**Previous Pattern (repeated in multiple files):**
```python
# Use LANCZOS for Pillow 10+ compatibility (ANTIALIAS was deprecated)
resample = getattr(Image, 'LANCZOS', getattr(Image, 'ANTIALIAS', None))
corner = corner.resize((radius, radius), resample)
```

**Implemented Solution (2025-10-10):**
Created compatibility module with reusable patterns:

```python
# phatch/lib/pillow_compat.py
"""Pillow version compatibility helpers."""

from PIL import Image

def get_resample_filter(name):
    """Get resampling filter compatible with all Pillow versions.

    Args:
        name: Filter name ('LANCZOS', 'BILINEAR', 'BICUBIC', 'NEAREST')

    Returns:
        PIL Image resampling constant
    """
    # Pillow 10+ renames
    COMPAT_MAP = {
        'LANCZOS': ('LANCZOS', 'ANTIALIAS'),  # Try new, fallback to old
        'BILINEAR': ('BILINEAR', 'LINEAR'),
    }

    names = COMPAT_MAP.get(name, (name,))
    for filter_name in names:
        if hasattr(Image, filter_name):
            return getattr(Image, filter_name)

    raise AttributeError(f"No resampling filter found for {name}")

def ensure_int_color(color):
    """Ensure color tuple contains integers (Pillow 10+ requirement).

    Args:
        color: Color as (R, G, B) or (R, G, B, A)

    Returns:
        Color tuple with integer values
    """
    return tuple(int(c) for c in color)
```

**New Usage:**
```python
from lib import pillow_compat

# Instead of:
resample = getattr(Image, 'LANCZOS', getattr(Image, 'ANTIALIAS', None))
corner = corner.resize((radius, radius), resample)

# Use:
corner = corner.resize((radius, radius), pillow_compat.LANCZOS)

# Or with function:
resample = pillow_compat.get_resample_filter('BILINEAR')
```

**Completed (2025-10-10):**
- ✅ Created `phatch/lib/pillow_compat.py` module
- ✅ Implemented `get_resample_filter(name)` function with fallback logic
- ✅ Implemented `ensure_int_color(color)` helper for color conversion
- ✅ Added convenience aliases: `LANCZOS`, `BILINEAR`, `BICUBIC`, `NEAREST`
- ✅ Created comprehensive test suite (24 tests in `tests/unit/lib/test_pillow_compat.py`)
- ✅ Updated 4 action files to use new helpers:
  - `round.py` - LANCZOS compatibility
  - `grid.py` - LANCZOS compatibility
  - `contour.py` - LANCZOS compatibility (2 occurrences)
  - `reflection.py` - BILINEAR compatibility
- ✅ All 2034 tests pass - zero regressions ✓
- ✅ Eliminated repeated compatibility code (DRY principle)

**Benefits Achieved:**
- ✓ DRY (Don't Repeat Yourself) - single source of truth
- ✓ Easy to update when Pillow changes again
- ✓ Self-documenting with comprehensive docstrings
- ✓ Well-tested (24 unit tests + integration tests)
- ✓ Backward compatible with Pillow 9.x and 10.x

**Effort:** 1 day (as estimated)
**Status:** COMPLETE

---

## Priority 3: Code Quality Improvements

### 3. Test Fixture Consolidation

**Issue:**
Common test fixtures are repeated across multiple test files.

**Example:**
```python
# In multiple test_*.py files:
@pytest.fixture
def rgb_image():
    return Image.new('RGB', (100, 100), 'red')
```

**Solution:**
Already partially addressed in `tests/unit/conftest.py`. Continue consolidating.

**Effort:** Ongoing
**Priority:** Low (cleanup, not blocking)

### 4. Action Interface Consistency ✅ COMPLETED

**Issue:**
Actions use either `pil()` staticmethod OR `apply()` method, with no clear pattern.

**Investigation Results (2025-10-10):**
- Analyzed all 54 action files
- Found clear pattern: 72% use `pil()`, 28% use `apply()`
- Pattern is intentional and well-designed:
  - **`pil()` staticmethod** (39 actions): Pure PIL image transformations, no metadata
  - **`apply()` method** (16 actions): File I/O, metadata ops, external tools

**Pattern Rules Discovered:**

**Use `pil()` when:**
- Pure image transformation (in-memory PIL operations)
- Only needs image object + parameters
- Returns modified PIL Image
- No metadata access needed
- Stateless operation

**Use `apply()` when:**
- Needs to read/write photo.info (metadata)
- Performs file I/O (save, copy, rename)
- Modifies EXIF/IPTC metadata
- Calls external tools (ImageMagick, jpegtran)
- Complex workflow requiring context
- Stateful operation

**Examples:**
- `rotate.py`: Uses `pil()` - pure image rotation
- `scale.py`: Uses `apply()` - modifies DPI metadata + resizes
- `save.py`: Uses `apply()` - writes files to disk
- `watermark.py`: Uses `pil()` - composites images in memory

**Completed (2025-10-10):**
- ✅ Analyzed 54 action files
- ✅ Documented pattern in `docs/ACTION_INTERFACE_PATTERNS.md`
- ✅ Created comprehensive guide with:
  - When to use each pattern
  - Implementation examples
  - Migration guide
  - Testing implications
  - Best practices

**Effort:** 1 day (investigation + documentation)
**Status:** COMPLETE

---

## Bonus: GUI Bug Fixes (Discovered During Refactoring)

While working through the refactoring plan, we discovered and fixed several critical wxPython 4.x GUI bugs:

### Console Mode Bugs ✅ FIXED (2025-10-10)

**Critical Python 3 compatibility issues that broke console mode entirely:**

1. **`api.init()` was commented out** - Actions weren't being loaded
2. **`u()` function returned bytes instead of str** - `TypeError` on stdout.write()
3. **Float division broke progress bar** - String multiplication requires int

**Files Fixed:** `phatch/console/console.py`
**Impact:** Console mode completely functional again

### Dropdown Widget Issues ✅ FIXED (2025-10-10)

**Issue:** Dropdowns closed immediately on click or turned grey/unresponsive

**Root Causes:**
1. **Event timing** - `EVT_CHOICE` fired synchronously, triggering tree rebuild that closed dropdown
2. **Widget destruction** - `update_form_relevance()` called during dropdown interaction deleted active widgets

**Fixes:**
1. Use `wx.CallAfter()` to defer callbacks (`popup.py`)
2. Move `update_form_relevance()` to after popup closes (`treeEdit.py`)
3. Ensure all fields with choices use ChoiceCtrl consistently (`treeEdit.py`)

**Files Fixed:**
- `phatch/lib/pyWx/popup.py`
- `phatch/lib/pyWx/treeEdit.py`

**Impact:** All dropdowns (Resolution, Folder, etc.) now work correctly

### Sizer Flags Assertion Errors ✅ FIXED (2025-10-10)

**Issue:** `wx.ALIGN_CENTER_VERTICAL` used in vertical sizers (not allowed in wxPython 4.x)

**Fix:** Removed incompatible alignment flags from vertical sizer items

**Files Fixed:** `phatch/pyWx/wxGlade/dialogs.py`

**Impact:** Execute dialog opens without assertion errors

### Color Picker Issues ✅ FIXED (2025-10-10)

**Issues:**
1. **Widget destruction during modal dialog** - `RuntimeError: wrapped C/C++ object deleted`
2. **Color wheel appeared all black** - Default color was black, making HSV picker unusable
3. **Deprecation warnings** - `wx.NamedColour()`, `menu.AppendItem()`

**Fixes:**
1. Excluded ColorField from `EVT_LEAVE_WINDOW` binding to prevent premature destruction
2. Properly convert HTML color strings to `wx.Colour` objects
3. Changed Border action default from black (#000000) to white (#FFFFFF)
4. Updated deprecated APIs: `wx.NamedColour` → `wx.Colour`, `AppendItem` → `Append`

**Files Fixed:**
- `phatch/lib/pyWx/popup.py`
- `phatch/lib/pyWx/treeEdit.py`
- `phatch/actions/border.py`
- `phatch/pyWx/dialogs.py`

**Impact:** Color picker fully functional with visible color wheel

### Summary of GUI Fixes

- **Console Mode:** 3 critical bugs fixed, now fully functional
- **Dropdowns:** Event timing and widget lifecycle issues resolved
- **Dialogs:** Sizer flags corrected for wxPython 4.x
- **Color Picker:** 4 issues fixed (destruction, initialization, defaults, deprecations)
- **All 2034 tests pass** after fixes

These fixes significantly improve the user experience and ensure compatibility with wxPython 4.x (Phoenix).

---

## Future Considerations

### Type Hints
- Add type hints to improve IDE support and catch errors
- Use mypy for static type checking
- Effort: 1-2 weeks
- Priority: Low (Python 3 compatible code works without hints)

### Async/Await for Batch Processing
- Consider async processing for performance
- May benefit from Python 3's asyncio
- Effort: 2-3 weeks
- Priority: Low (performance is acceptable)

### Configuration as Code
- Currently uses custom field types (SliderField, ColorField, etc.)
- Consider dataclasses or pydantic for type safety
- Effort: 3-4 weeks
- Priority: Very Low (would be major rewrite)

---

## Refactoring Strategy

### Phase 1: Complete Testing (Current)
- Reach 60% test coverage (~1400 tests)
- Test remaining ~25 actions
- Document issues as discovered
- **Status:** In Progress (52% coverage, 30/55 actions)

### Phase 2: High Priority Refactoring
- Fix lazy-loading testability (Priority 1)
- Create Pillow compatibility module (Priority 2)
- **Timing:** After reaching 60% coverage
- **Approach:** With comprehensive tests as safety net

### Phase 3: Code Quality
- Consolidate fixtures
- Document action patterns
- **Timing:** As time permits
- **Approach:** Incremental improvements

### Phase 4: Future Enhancements
- Type hints
- Performance improvements
- **Timing:** Post-migration
- **Approach:** New feature development

---

## Success Metrics

### Testing (Phase 1)
- [x] 1135/1400+ tests passing (81% of 60% goal)
- [x] 30/55 actions tested (55%)
- [ ] 35/55 actions tested (64%) - Target
- [ ] 60% overall code coverage

### Refactoring (Phase 2)
- [x] Lazy-loading dependencies injectable
- [x] Pillow compatibility module created
- [x] All tests still passing after refactor (2034 tests passing)
- [ ] Watermark tests completed (15 additional tests)

### Code Quality (Phase 3)
- [x] No repeated compatibility code (pillow_compat module eliminates duplication)
- [x] Action patterns documented (ACTION_INTERFACE_PATTERNS.md created)
- [ ] Test fixtures fully consolidated (ongoing, low priority)

---

## Notes

**Migration Philosophy:**
- "Make it work, make it right, make it fast" - Kent Beck
- Currently: "Make it work" (Python 3 compatible)
- Testing phase: "Make it right" (test coverage)
- Refactoring phase: "Make it better" (clean code)

**Risk Management:**
- Comprehensive tests BEFORE refactoring
- One change at a time
- Keep all tests passing
- No "big bang" rewrites

**References:**
- SOLID Principles (especially Dependency Inversion)
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple, Stupid)
- TDD (Test-Driven Development)

---

---

## Refactoring Session Summary (2025-10-10)

**Major Accomplishments:**

✅ **Priority 0:** Updated all dependencies to latest secure versions
✅ **Priority 1:** Implemented dependency injection for 43 actions
✅ **Priority 2:** Created Pillow 10+ compatibility module
✅ **Priority 3:** Documented action interface patterns (pil vs apply)
✅ **Bonus:** Fixed 10+ critical GUI bugs (console, dropdowns, dialogs, color picker)

**Test Coverage:**
- 2034 tests passing (started with 2010)
- 24 new tests for pillow_compat module
- Zero regressions throughout refactoring

**Code Quality:**
- Eliminated repeated compatibility code (DRY)
- Added comprehensive documentation
- Fixed wxPython 4.x compatibility issues
- Improved user experience with better defaults

**Remaining Low-Priority Tasks:**
- ✅ Test fixture consolidation (shared image fixtures, 2025-02-14)
- Watermark tests completion (15 additional tests - now possible with dependency injection)

**Overall Status:** Phase 2 refactoring COMPLETE ✅

---

Last Updated: 2025-10-10
Maintained By: Development Team

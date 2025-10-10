# Phatch Refactoring Needs

This document tracks technical debt and refactoring opportunities identified during the Python 3 migration and test modernization effort.

## Priority 1: High Impact, Medium Effort

### 1. Lazy-Loaded Dependencies Testability

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

**Effort:** 2-3 days
- Update init() pattern in ~20 affected actions
- Update corresponding tests
- Verify no regression in production use

**Priority:** Medium
- Blocking: 15 watermark tests incomplete
- Not blocking: 1135+ other tests pass without this change

---

## Priority 2: Medium Impact, Low Effort

### 2. Pillow 10+ Compatibility Pattern

**Issue:**
Several Pillow constants were renamed in version 10+, requiring compatibility code.

**Discovered During Testing:**
- `Image.LINEAR` → `Image.BILINEAR` (reflection.py:62)
- `Image.ANTIALIAS` → `Image.LANCZOS` (round.py:122) - **FIXED** (grid.py:69)
- Float color values need int conversion for `Image.new()` (reflection.py:85-87)
- `ImageDraw.textsize()` → `ImageDraw.textbbox()` (text.py:55) - **FIXED**
- Undefined `message` variable (openImage.py:72) - **FIXED**
- Dictionary iteration during modification (delete_tags.py:47-52) - **FIXED**
  - Python 3 requires `list(dict.keys())` when modifying dict during iteration
  - Also fixed: `method == 'all'` should check `METHODS[0]` for proper translation

**Current Pattern (repeated in multiple files):**
```python
# Use LANCZOS for Pillow 10+ compatibility (ANTIALIAS was deprecated)
resample = getattr(Image, 'LANCZOS', getattr(Image, 'ANTIALIAS', None))
corner = corner.resize((radius, radius), resample)
```

**Proposed Solution:**
Create compatibility module for reusable patterns:

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

**Usage:**
```python
from lib.pillow_compat import get_resample_filter, ensure_int_color

# Instead of:
resample = getattr(Image, 'LANCZOS', getattr(Image, 'ANTIALIAS', None))

# Use:
resample = get_resample_filter('LANCZOS')
```

**Benefits:**
- DRY (Don't Repeat Yourself)
- Single source of truth for compatibility
- Easy to update when Pillow changes again
- Self-documenting

**Effort:** 1 day
- Create pillow_compat.py module
- Update 3-5 affected actions
- Add unit tests for compatibility helpers

**Priority:** Low-Medium
- Not blocking: Current inline code works
- Tech debt: Repeated code in multiple files

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

### 4. Action Interface Consistency

**Issue:**
Actions use either `pil()` staticmethod OR `apply()` method, with no clear pattern.

**Examples:**
- rotate.py: Uses `pil = staticmethod(rotate)`
- scale.py: Uses `apply()` method
- watermark.py: Uses `pil = staticmethod(watermark)`

**Investigation Needed:**
- Document when to use each pattern
- Check if this is intentional design or inconsistency
- May be correct: simple transforms use pil(), complex workflows use apply()

**Effort:** 2-3 days (investigation + documentation)
**Priority:** Low (works as-is, documentation would help)

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
- [ ] Lazy-loading dependencies injectable
- [ ] Pillow compatibility module created
- [ ] All tests still passing after refactor
- [ ] Watermark tests completed (15 additional tests)

### Code Quality (Phase 3)
- [ ] No repeated compatibility code
- [ ] Action patterns documented
- [ ] Test fixtures fully consolidated

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

Last Updated: 2025-10-09
Maintained By: Development Team

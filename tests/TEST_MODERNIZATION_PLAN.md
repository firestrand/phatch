# Test Modernization & Coverage Plan

**Project**: Phatch - Photo Batch Processor
**Created**: 2025-10-08
**Status**: Planning
**Goal**: Achieve 80%+ test coverage with modern, maintainable test structure

## Executive Summary

Following the successful Python 3 migration of the test infrastructure, this plan outlines the strategy to:
1. Reorganize tests following modern best practices
2. Achieve 80%+ code coverage through systematic testing
3. Apply SOLID, DRY, and KISS principles throughout
4. Create a maintainable foundation for ongoing development

## Current State Assessment

### Coverage Baseline
- **Current Coverage**: 1.7%
- **Files**: ~100+ Python files in phatch/
- **Actions**: 50+ image processing action modules
- **Core Modules**: ~20 core framework modules

### Existing Tests
- `pep8_test.py` - Code quality (ruff)
- `license_test.py` - License headers (optional)
- `doc_test.py` - Docstring examples
- `acceptance_test.py` - End-to-end testing framework (not integrated with pytest)

### Issues with Current Structure
1. **No Unit Tests**: Only linting and doctests run via pytest
2. **Poor Organization**: Tests not organized by module or type
3. **Low Coverage**: 1.7% - essentially no code coverage
4. **Missing Test Types**: No integration tests, minimal unit tests
5. **Acceptance Tests Separate**: Not integrated with pytest framework

## Principles

All new tests and refactoring will follow:

- **SOLID**:
  - **S**ingle Responsibility: Each test tests one thing
  - **O**pen/Closed: Tests extensible without modification
  - **L**iskov Substitution: Mock objects behave like real ones
  - **I**nterface Segregation: Test fixtures focused and minimal
  - **D**ependency Inversion: Test against interfaces, not implementations

- **DRY** (Don't Repeat Yourself):
  - Shared fixtures in conftest.py
  - Reusable test utilities
  - Parametrized tests where appropriate

- **KISS** (Keep It Simple):
  - Clear, readable test names
  - Minimal setup/teardown
  - Focused assertions

- **TDD** (Test-Driven Development):
  - Write failing test first
  - Implement minimum code to pass
  - Refactor with confidence

## Modern Test Structure

### Proposed Directory Layout

```
tests/
├── README.md                    # Test documentation (exists)
├── conftest.py                  # Shared fixtures (exists)
├── pytest.ini                   # Pytest config (exists)
├── requirements-dev.txt         # Test dependencies (exists)
├── TEST_MODERNIZATION_PLAN.md   # This document
│
├── unit/                        # Unit tests (NEW)
│   ├── __init__.py
│   ├── conftest.py             # Unit test fixtures
│   ├── actions/                # Test phatch/actions/
│   │   ├── __init__.py
│   │   ├── test_scale.py
│   │   ├── test_rotate.py
│   │   ├── test_save.py
│   │   └── ...
│   ├── core/                   # Test phatch/core/
│   │   ├── __init__.py
│   │   ├── test_api.py
│   │   ├── test_config.py
│   │   ├── test_models.py
│   │   ├── test_pil.py
│   │   └── ...
│   ├── lib/                    # Test phatch/lib/
│   │   ├── __init__.py
│   │   ├── test_imtools.py
│   │   ├── test_metadata.py
│   │   ├── test_fonts.py
│   │   └── ...
│   └── console/                # Test phatch/console/
│       ├── __init__.py
│       └── test_console.py
│
├── integration/                 # Integration tests (NEW)
│   ├── __init__.py
│   ├── conftest.py             # Integration fixtures
│   ├── test_action_pipeline.py # Test action chaining
│   ├── test_file_operations.py # Test actual file I/O
│   ├── test_metadata_ops.py    # Test metadata reading/writing
│   └── ...
│
├── functional/                  # Functional/acceptance tests (REFACTORED)
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_actionlists.py     # Refactored from acceptance_test.py
│   ├── test_image_processing.py
│   └── fixtures/               # Test images and data
│       ├── images/
│       └── actionlists/
│
├── quality/                     # Code quality tests (REORGANIZED)
│   ├── __init__.py
│   ├── test_pep8.py            # Moved from root
│   ├── test_license.py         # Moved from root
│   └── test_doctests.py        # Moved from root
│
└── fixtures/                    # Shared test data (NEW)
    ├── images/                 # Sample test images (from current input/)
    ├── actionlists/
    └── expected_outputs/
```

### Test Type Definitions

#### Unit Tests (`unit/`)
- **Purpose**: Test individual functions/classes in isolation
- **Characteristics**:
  - Fast execution (< 100ms per test)
  - No file I/O (use mocks)
  - No external dependencies
  - High coverage of edge cases
- **Example**: Testing `phatch.core.pil.apply_resize()` with mocked PIL.Image

#### Integration Tests (`integration/`)
- **Purpose**: Test components working together
- **Characteristics**:
  - May use actual file I/O
  - Test interaction between modules
  - Verify data flows correctly
  - Slower than unit tests (< 1s per test)
- **Example**: Testing action pipeline execution with real images

#### Functional Tests (`functional/`)
- **Purpose**: End-to-end workflows and user scenarios
- **Characteristics**:
  - Complete workflows (load → process → save)
  - Use real images and actionlists
  - Verify expected outputs
  - Slowest tests (1-10s per test)
- **Example**: Process batch of images through complete actionlist

#### Quality Tests (`quality/`)
- **Purpose**: Code quality, standards, documentation
- **Characteristics**:
  - Linting (ruff)
  - License headers
  - Doctests
  - Documentation completeness
- **Example**: PEP8 compliance, license header validation

## Phased Implementation Plan

### Phase 1: Foundation & Core Testing (Target: 30% coverage)
**Duration**: 2-3 weeks
**Priority**: HIGH - Critical path functionality

#### 1.1 Create Test Infrastructure
- [x] Set up pytest configuration (done in migration)
- [x] Create conftest.py with shared fixtures (done)
- [ ] Create unit/, integration/, functional/, quality/ directories
- [ ] Create __init__.py files for all test directories
- [ ] Create fixtures/ directory with sample test data
- [ ] Set up coverage reporting workflow

#### 1.2 Core Module Unit Tests
Focus on `phatch/core/` - the heart of the application:

**Priority 1: `core/models.py`**
- Test `Action` base class
- Test action interface validation
- Test action parameter handling
- Coverage target: 90%+

**Priority 2: `core/config.py`**
- Test path initialization
- Test config file handling
- Test platform-specific paths
- Coverage target: 85%+

**Priority 3: `core/api.py`**
- Test actionlist loading/saving
- Test batch execution framework
- Test error handling
- Coverage target: 80%+

**Priority 4: `core/pil.py`**
- Test PIL/Pillow utilities
- Test image format handling
- Test colorspace conversions
- Coverage target: 85%+

**Priority 5: `core/message.py`**
- Test pub/sub messaging
- Test message routing
- Test receiver registration
- Coverage target: 90%+

#### 1.3 Example Test Structure

Create `tests/unit/core/test_models.py`:
```python
import pytest
from phatch.core import models

class TestActionBase:
    """Test the base Action class."""

    def test_action_has_required_attributes(self):
        """Action class should have required metadata attributes."""
        assert hasattr(models.Action, 'label')
        assert hasattr(models.Action, 'author')
        assert hasattr(models.Action, 'version')

    def test_action_interface_method_exists(self):
        """Action class should have interface() method."""
        assert hasattr(models.Action, 'interface')
        assert callable(models.Action.interface)

    @pytest.mark.parametrize("field_type", [
        "SliderField", "FileField", "ChoiceField", "TextField"
    ])
    def test_action_has_field_types(self, field_type):
        """Action should provide common field types."""
        assert hasattr(models.Action, field_type)
```

### Phase 2: Action Plugin Testing (Target: 60% coverage)
**Duration**: 4-6 weeks
**Priority**: MEDIUM - Feature coverage

#### 2.1 Create Action Test Framework
- [ ] Create shared fixtures for test images
- [ ] Create action test base class with common assertions
- [ ] Create helper functions for image comparison
- [ ] Set up parametrized tests for common operations

#### 2.2 Priority Actions to Test
Test the most commonly used and critical actions first:

**Tier 1: Essential Actions (90%+ coverage)**
- `save.py` - File saving (critical!)
- `scale.py` - Image resizing
- `rotate.py` - Image rotation
- `crop.py` - Image cropping

**Tier 2: Common Actions (85%+ coverage)**
- `border.py` - Add borders
- `canvas.py` - Canvas manipulation
- `fit.py` - Fit to dimensions
- `mirror.py` - Flip/mirror
- `watermark.py` - Add watermarks
- `text.py` - Add text

**Tier 3: Effects Actions (75%+ coverage)**
- `shadow.py` - Drop shadows
- `reflection.py` - Reflections
- `perspective.py` - Perspective transform
- `round.py` - Rounded corners
- `mask.py` - Masking

**Tier 4: Color Actions (70%+ coverage)**
- `brightness.py`, `contrast.py`, `saturation.py`
- `colorize.py`, `desaturate.py`
- `autocontrast.py`, `equalize.py`
- `invert.py`, `solarize.py`

**Tier 5: Advanced Actions (60%+ coverage)**
- All remaining actions in phatch/actions/

#### 2.3 Action Test Template

Create `tests/unit/actions/test_scale.py`:
```python
import pytest
from PIL import Image
from phatch.actions import scale

@pytest.fixture
def sample_image():
    """Create a simple test image."""
    return Image.new('RGB', (100, 100), color='red')

class TestScaleAction:
    """Test the Scale action."""

    def test_scale_down_by_percentage(self, sample_image):
        """Scale image down by percentage."""
        result = scale.Action.pil(sample_image, width='50%', height='50%')
        assert result.size == (50, 50)

    def test_scale_to_absolute_size(self, sample_image):
        """Scale image to absolute dimensions."""
        result = scale.Action.pil(sample_image, width='200', height='200')
        assert result.size == (200, 200)

    def test_scale_maintains_aspect_ratio(self, sample_image):
        """Scale should maintain aspect ratio when specified."""
        # Test implementation
        pass

    @pytest.mark.parametrize("width,height,expected", [
        ('50%', '50%', (50, 50)),
        ('200', '100', (200, 100)),
        ('25%', '75%', (25, 75)),
    ])
    def test_scale_various_sizes(self, sample_image, width, height, expected):
        """Test scaling with various size specifications."""
        result = scale.Action.pil(sample_image, width=width, height=height)
        assert result.size == expected
```

### Phase 3: Library & Utilities (Target: 75% coverage)
**Duration**: 2-3 weeks
**Priority**: MEDIUM - Supporting functionality

#### 3.1 Test `phatch/lib/` modules

**Priority modules:**
- `imtools.py` - Image manipulation utilities (90% coverage)
- `metadata.py` - EXIF/IPTC handling (85% coverage)
- `fonts.py` - Font handling (80% coverage)
- `colors.py` - Color utilities (85% coverage)
- `formField.py` - Form field definitions (80% coverage)
- `odict.py` - Ordered dictionary (90% coverage)
- `safe.py` - Safe evaluation (90% coverage)

### Phase 4: Integration & Functional Tests (Target: 80% coverage)
**Duration**: 2-3 weeks
**Priority**: HIGH - Validate real-world usage

#### 4.1 Integration Tests
- [ ] Action pipeline execution
- [ ] File I/O with various formats (PNG, JPEG, GIF, TIFF)
- [ ] Metadata preservation across operations
- [ ] Error handling and recovery
- [ ] Multi-action workflows

#### 4.2 Functional Tests
- [ ] Refactor acceptance_test.py into pytest
- [ ] Test complete actionlists from data/actionlists/
- [ ] Test batch processing of image collections
- [ ] Verify output matches expected results
- [ ] Test console mode workflows

Example `tests/integration/test_action_pipeline.py`:
```python
import pytest
from pathlib import Path
from phatch.core import api

class TestActionPipeline:
    """Test executing multiple actions in sequence."""

    def test_scale_then_save(self, tmp_path, test_input_dir):
        """Scale an image then save it."""
        # Create actionlist
        actions = [
            {'action': 'scale', 'width': '50%', 'height': '50%'},
            {'action': 'save', 'path': str(tmp_path)}
        ]

        # Execute on test image
        input_image = test_input_dir / 'bee.png'
        api.execute_actionlist(actions, [input_image])

        # Verify output
        output_file = tmp_path / 'bee.png'
        assert output_file.exists()

        # Verify size
        from PIL import Image
        result = Image.open(output_file)
        # Original bee.png is 100x100, scaled to 50%
        assert result.size == (50, 50)
```

### Phase 5: GUI & Console Testing (Target: 85% coverage)
**Duration**: 2-3 weeks
**Priority**: MEDIUM - UI testing

#### 5.1 Console Tests
- Test `phatch/console/` modules
- Mock terminal I/O
- Test progress display
- Test error reporting

#### 5.2 GUI Tests (Challenging)
- Use pytest-qt or similar for wxPython
- Test critical GUI operations
- Focus on non-UI logic in `phatch/pyWx/`
- May require mocking wx components

### Phase 6: Polish & Maintenance (Target: 90% coverage)
**Duration**: 1-2 weeks
**Priority**: LOW - Refinement

#### 6.1 Increase Coverage
- Identify and test edge cases
- Add parametrized tests for coverage gaps
- Test error conditions and exceptions
- Test platform-specific code paths

#### 6.2 Test Maintenance
- Document test patterns in README
- Create test writing guidelines
- Set up CI/CD integration
- Configure coverage reporting

## Coverage Targets by Module

| Module Category | Target Coverage | Priority |
|----------------|----------------|----------|
| phatch/core/ | 85%+ | HIGH |
| phatch/actions/ (Tier 1) | 90%+ | HIGH |
| phatch/actions/ (Tier 2) | 85%+ | MEDIUM |
| phatch/actions/ (Tier 3-5) | 70%+ | MEDIUM |
| phatch/lib/ | 80%+ | MEDIUM |
| phatch/console/ | 75%+ | MEDIUM |
| phatch/pyWx/ (non-UI) | 70%+ | LOW |
| **Overall Project** | **80%+** | **GOAL** |

## Test Writing Guidelines

### Naming Conventions
- Test files: `test_<module>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<what_it_tests>`
- Be descriptive: `test_scale_maintains_aspect_ratio_when_constrained`

### Test Structure (AAA Pattern)
```python
def test_something():
    # Arrange - Set up test data and conditions
    image = create_test_image(100, 100)
    action = ScaleAction()

    # Act - Execute the code under test
    result = action.pil(image, width='50%', height='50%')

    # Assert - Verify the results
    assert result.size == (50, 50)
```

### Use Fixtures for Common Setup
```python
@pytest.fixture
def test_image_100x100():
    """Create a 100x100 test image."""
    return Image.new('RGB', (100, 100), color='blue')

def test_with_fixture(test_image_100x100):
    # Use the fixture
    assert test_image_100x100.size == (100, 100)
```

### Parametrize for Multiple Cases
```python
@pytest.mark.parametrize("input_val,expected", [
    (10, 20),
    (5, 10),
    (0, 0),
])
def test_double(input_val, expected):
    assert double(input_val) == expected
```

### Mock External Dependencies
```python
from unittest.mock import Mock, patch

def test_save_calls_pil_save(tmp_path):
    mock_image = Mock(spec=Image.Image)
    save_path = tmp_path / 'output.png'

    save_action.pil(mock_image, path=str(save_path))

    mock_image.save.assert_called_once()
```

## Success Criteria

### Phase 1 Success
- [x] Modern test structure in place
- [ ] Core modules have 30%+ coverage
- [ ] All core module tests passing
- [ ] CI/CD running tests automatically

### Phase 2 Success
- [ ] Top 20 actions have comprehensive tests
- [ ] Action test coverage at 60%+
- [ ] Shared action test utilities documented
- [ ] All action tests passing

### Phase 3 Success
- [ ] All lib/ modules tested
- [ ] Overall coverage at 75%+
- [ ] No critical bugs in utilities

### Phase 4 Success
- [ ] Integration tests cover main workflows
- [ ] Functional tests replace acceptance_test.py
- [ ] Coverage at 80%+
- [ ] All tests passing in CI/CD

### Phase 5 Success
- [ ] Console and GUI tested where feasible
- [ ] Coverage at 85%+
- [ ] Test suite runs in < 5 minutes

### Final Success
- [ ] **Overall coverage: 80%+** ✨
- [ ] All tests documented
- [ ] Test writing guide complete
- [ ] CI/CD fully configured
- [ ] Maintainable test foundation established

## Timeline Estimate

| Phase | Duration | Cumulative | Coverage Goal |
|-------|----------|------------|---------------|
| Phase 1: Foundation & Core | 2-3 weeks | Week 3 | 30% |
| Phase 2: Action Plugins | 4-6 weeks | Week 9 | 60% |
| Phase 3: Libraries | 2-3 weeks | Week 12 | 75% |
| Phase 4: Integration/Functional | 2-3 weeks | Week 15 | 80% |
| Phase 5: GUI/Console | 2-3 weeks | Week 18 | 85% |
| Phase 6: Polish | 1-2 weeks | Week 20 | 90% |

**Total Estimated Duration**: 13-20 weeks (3-5 months)

This timeline assumes:
- Part-time development (10-20 hours/week)
- Following TDD principles (write tests first)
- Regular refactoring as needed
- No major blocking issues

## Getting Started

### Immediate Next Steps

1. **Create directory structure** (Day 1):
   ```bash
   cd tests
   mkdir -p unit/{actions,core,lib,console}
   mkdir -p integration functional quality fixtures
   touch unit/__init__.py integration/__init__.py functional/__init__.py quality/__init__.py
   ```

2. **Move existing quality tests** (Day 1):
   ```bash
   mv pep8_test.py quality/test_pep8.py
   mv license_test.py quality/test_license.py
   mv doc_test.py quality/test_doctests.py
   ```

3. **Create first unit test** (Day 2):
   - Start with `tests/unit/core/test_models.py`
   - Test the base `Action` class
   - Verify attributes and methods exist
   - Run: `pytest tests/unit/core/test_models.py`

4. **Set up coverage workflow** (Day 2):
   ```bash
   pytest --cov=phatch --cov-report=html --cov-report=term
   ```

5. **Begin Phase 1** (Week 1):
   - Focus on core module tests
   - Aim for 30% coverage by end of week 3
   - Document patterns as you go

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest fixtures guide](https://docs.pytest.org/en/stable/fixture.html)
- [pytest parametrize](https://docs.pytest.org/en/stable/parametrize.html)
- [Python Mock/Patch](https://docs.python.org/3/library/unittest.mock.html)
- [TDD by Example](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530)
- [Coverage.py](https://coverage.readthedocs.io/)

## Conclusion

This plan provides a clear roadmap to achieve 80%+ test coverage while following modern best practices. By organizing tests into logical categories, applying SOLID/DRY/KISS principles, and following a phased approach, we can build a maintainable and comprehensive test suite that provides confidence in Phatch's reliability and makes future development safer and faster.

The key to success is starting small (Phase 1 core tests), building momentum, and maintaining discipline in following TDD principles throughout the journey.
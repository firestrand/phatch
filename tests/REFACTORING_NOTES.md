# Refactoring Notes - SOLID, DRY, KISS Improvements

This document tracks opportunities to improve code quality following SOLID, DRY, and KISS principles discovered during test creation.

## Core Modules

### phatch/core/message.py

**Issue**: Tight coupling between messaging and file I/O
**Principle**: Single Responsibility Principle (SOLID)
**Location**: `ProgressReceiver.update_filename()` at line 98-105
**Problem**: The update_filename method directly uses `os.path.split` and string formatting to create messages. This mixes progress tracking with file path manipulation.

**Suggested Improvement**:
```python
# Extract filename formatting to a separate function
def format_filename_message(filename):
    dirname, basename = os.path.split(filename)
    dirname = ensure_unicode(dirname)
    basename = ensure_unicode(basename)
    return "%s: %s\n%s: %s\n" % (_('In'), dirname, _('File'), basename)

# Then in ProgressReceiver:
def update_filename(self, result, parent_index, filename):
    message = format_filename_message(filename)
    self.update(result, parent_index * self.child_max, newmsg=message)
    self.sleep()
```

**Benefits**: Better testability, clearer separation of concerns

---

**Issue**: Magic numbers in progress calculation
**Principle**: DRY (Don't Repeat Yourself)
**Location**: `ProgressReceiver.update_index()` at line 107
**Problem**: Formula `parent_index * self.child_max + child_index + 1` appears without explanation

**Suggested Improvement**:
```python
def _calculate_progress_value(self, parent_index, child_index):
    """Calculate progress value from parent and child indices.

    Formula: parent_index * child_max + child_index + 1
    The +1 accounts for 1-based indexing in progress display.
    """
    return parent_index * self.child_max + child_index + 1

def update_index(self, result, parent_index, child_index):
    value = self._calculate_progress_value(parent_index, child_index)
    self.update(result, value)
```

**Benefits**: Self-documenting code, easier to test and modify

---

**Issue**: Empty default implementations
**Principle**: KISS (Keep It Simple, Stupid)
**Location**: `FrameReceiver` and `ProgressReceiver` at lines 50-78, 111-118
**Problem**: Multiple methods with `pass` bodies suggest these classes might be better as abstract base classes or protocols.

**Suggested Improvement**:
```python
from abc import ABC, abstractmethod

class FrameReceiverProtocol(ABC):
    """Protocol for frame receivers."""

    @abstractmethod
    def show_error(self, message):
        """Display error message to user."""
        pass

    # ... other abstract methods ...

class DefaultFrameReceiver(FrameReceiverProtocol):
    """Default implementation that does nothing."""

    def show_error(self, message):
        pass  # No-op implementation
```

**Benefits**: Clearer intent, better type checking, explicit contracts

---

### phatch/core/config.py

**Issue**: Global state mutation
**Principle**: Single Responsibility Principle (SOLID)
**Location**: `check_config_paths()` at lines 109-160
**Problem**: Function both computes values AND mutates global variables

**Suggested Improvement**:
```python
class ConfigPaths:
    """Encapsulates configuration paths."""

    def __init__(self, custom_paths=None):
        self.is_system_install = False
        self._initialize_paths(custom_paths)

    def _initialize_paths(self, custom_paths):
        if custom_paths:
            self.is_system_install = False
            self.data_path = custom_paths['PHATCH_DATA_PATH']
            # ...
        else:
            self.is_system_install = True
            # ...

# Replace global variables with a singleton instance
config_paths = ConfigPaths()
```

**Benefits**: Easier to test, no global state, clearer lifecycle

---

**Issue**: Monolithic initialization function
**Principle**: Single Responsibility Principle (SOLID)
**Location**: `init_config_paths()` at lines 214-243
**Problem**: Function does too many things: checks paths, configures sys.path, patches PIL, sets font cache, registers paths

**Suggested Improvement**:
```python
class ConfigInitializer:
    def __init__(self, config_paths=None):
        self.config_paths = config_paths or {}

    def initialize(self):
        """Initialize all configuration."""
        self._check_and_add_paths()
        self._configure_python_path()
        self._setup_font_cache()
        return self.config_paths

    def _check_and_add_paths(self):
        self.config_paths = check_config_paths(self.config_paths)
        add_user_paths(self.config_paths)

    def _configure_python_path(self):
        phatch_path = fix_python_path(self.config_paths.get('PHATCH_PYTHON_PATH'))
        fix_python_path(USER_ACTIONS_PATH)
        return phatch_path

    def _setup_font_cache(self):
        from phatch.lib.fonts import set_font_cache
        set_font_cache(USER_FONTS_PATH, PHATCH_FONTS_PATH,
                      USER_FONTS_CACHE_PATH, PHATCH_FONTS_CACHE_PATH)
```

**Benefits**: Each method has single responsibility, easier to test, clearer flow

---

**Issue**: Disabled code block
**Principle**: KISS
**Location**: `verify_app_user_paths()` at lines 88-99
**Problem**: Large commented-out code block (if 0:) creates confusion

**Suggested Improvement**:
- Remove the disabled code entirely
- If needed for reference, move to git history or separate documentation

**Benefits**: Cleaner code, less confusion

---

### phatch/core/models.py

**Issue**: Field definition mixed with class definition
**Principle**: Single Responsibility Principle (SOLID)
**Location**: Action class interface() method pattern
**Observation**: Action classes mix data model (fields) with behavior (pil processing)

**Suggested Improvement**: Consider separating field definitions from actions
```python
@dataclass
class ActionFieldSchema:
    """Define action parameter schema."""
    fields: dict

class Action:
    """Base action with processing logic."""
    schema = ActionFieldSchema(fields={})

    @classmethod
    def get_fields(cls):
        return cls.schema.fields

    @staticmethod
    def process(image, **params):
        """Process image - to be overridden."""
        return image
```

**Benefits**: Clearer separation, better introspection, easier validation

---

### phatch/core/ct.py

**Issue**: Re-export pattern for convenience
**Principle**: Explicit is better than implicit
**Location**: Lines 22-35 (USER_* path re-exports)
**Observation**: ct module re-exports paths from config for convenience, but this creates coupling

**Suggested Improvement**:
- Document WHY re-exports exist (developer convenience)
- Consider whether convenience outweighs coupling
- Alternative: Use explicit imports where needed

**Benefits**: More explicit dependencies, easier to understand module purpose

---

## General Patterns

### Translation System Initialization

**Issue**: Global `_` function requirement
**Principle**: Dependency Injection
**Location**: Multiple files requiring `builtins._ = lambda x: x` in tests
**Problem**: Tests need to pollute builtins to initialize modules

**Suggested Improvement**:
```python
# Instead of requiring global _
class TranslationManager:
    def __init__(self, translator=None):
        self.translator = translator or (lambda x: x)

    def translate(self, text):
        return self.translator(text)

# Inject translation manager instead of using global _
translation_manager = TranslationManager()

# In code:
label = translation_manager.translate('Save')
```

**Benefits**: Easier to test, no global pollution, explicit dependencies

---

### Import Organization

**Issue**: Inconsistent import paths
**Principle**: KISS
**Observation**: Some files use `from phatch.core import X`, others use `from core import X`
**Problem**: Creates confusion about module structure

**Suggested Improvement**:
- Standardize on absolute imports (`from phatch.core import X`)
- Update all files consistently
- Document import conventions in CONTRIBUTING.md

**Benefits**: Clearer module structure, easier refactoring

---

## Testing Improvements

### Mock Usage

**Observation**: Heavy use of mocking in tests suggests tight coupling
**Suggested Improvement**: Where possible, refactor to use dependency injection instead of mocking

**Example**:
```python
# Instead of:
@patch('phatch.core.config.subprocess.Popen')
def test_check_fonts(mock_popen):
    check_fonts()
    mock_popen.assert_called_once()

# Prefer:
class FontChecker:
    def __init__(self, subprocess_runner=None):
        self.subprocess_runner = subprocess_runner or subprocess.Popen

    def check_fonts(self):
        self.subprocess_runner([...])

# Test with injected mock:
def test_check_fonts():
    mock_runner = Mock()
    checker = FontChecker(subprocess_runner=mock_runner)
    checker.check_fonts()
    mock_runner.assert_called_once()
```

**Benefits**: More testable without mocking, clearer dependencies

---

## Priority Refactorings

Based on impact and feasibility:

1. **HIGH**: Extract ConfigPaths class (config.py) - improves testability significantly
2. **HIGH**: Split init_config_paths() into smaller functions - easier to understand and test
3. **MEDIUM**: Add ABC/Protocol for Receiver classes - clearer contracts
4. **MEDIUM**: Remove disabled code blocks - reduces confusion
5. **LOW**: Standardize imports - long-term maintainability

---

## Notes on Test Coverage

While creating tests, noticed:
- Some modules have high complexity (api.py: 935 lines) - candidates for splitting
- File I/O mixed with business logic in many places - hard to unit test
- Heavy reliance on inheritance for configuration - consider composition

---

## Document Maintenance

This document should be updated whenever:
1. New refactoring opportunities are discovered during testing
2. Refactorings are completed (move to CHANGELOG.md)
3. Design patterns are established (move to CONTRIBUTING.md)

Last updated: 2025-10-09 (Phase 1.2 - Core Module Testing)

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

### phatch/core/settings.py

**Issue**: Monolithic function doing multiple things
**Principle**: Single Responsibility Principle (SOLID)
**Location**: `create_settings()` function at lines 26-67
**Problem**: Function creates defaults, merges options, merges config_paths, and conditionally initializes config

**Suggested Improvement**:
```python
class SettingsBuilder:
    """Build settings dict step by step."""

    def __init__(self):
        self.settings = self._get_defaults()

    @staticmethod
    def _get_defaults():
        """Return default settings dictionary."""
        return {
            'extensions': IMAGE_READ_EXTENSIONS,
            'recursive': False,
            # ... all defaults ...
        }

    def merge_options(self, options):
        """Merge command-line options into settings."""
        if options:
            for attr in self.settings:
                if hasattr(options, attr):
                    self.settings[attr] = getattr(options, attr)
        return self

    def merge_config_paths(self, config_paths):
        """Merge configuration paths into settings."""
        if config_paths is None:
            from .config import init_config_paths
            config_paths = init_config_paths()
        self.settings.update(config_paths)
        return self

    def build(self):
        """Return final settings dict."""
        return self.settings

# Usage:
def create_settings(config_paths=None, options=None):
    return (SettingsBuilder()
            .merge_options(options)
            .merge_config_paths(config_paths)
            .build())
```

**Benefits**: Each method has single responsibility, easier to test, clearer flow, fluent interface

---

**Issue**: Magic default values scattered in code
**Principle**: DRY (Don't Repeat Yourself)
**Location**: Lines 28-57 (hardcoded defaults)
**Problem**: Default settings are defined inline, making them hard to find and modify

**Suggested Improvement**:
```python
# At module level or in separate config
DEFAULT_SETTINGS = {
    # Execute settings
    'extensions': IMAGE_READ_EXTENSIONS,
    'recursive': False,
    'stop_for_errors': True,
    # ... grouped logically ...
}

# Or even better, use dataclasses:
@dataclass
class PhatchSettings:
    """Phatch application settings with defaults."""
    # Execute settings
    extensions: List[str] = field(default_factory=lambda: IMAGE_READ_EXTENSIONS)
    recursive: bool = False
    stop_for_errors: bool = True
    # ...
```

**Benefits**: Centralized configuration, type hints, easier to document, better IDE support

---

**Issue**: FIXME comment indicates code smell
**Principle**: KISS (Keep It Simple, Stupid)
**Location**: Line 63 `#FIXME: when is this happening`
**Problem**: Conditional initialization of config_paths when None - unclear why this happens

**Suggested Improvement**:
1. Document when/why config_paths is None (startup vs testing vs API call)
2. Consider making config_paths required, or:
3. Use default parameter that makes intention clear:

```python
def create_settings(config_paths='auto', options=None):
    """Create settings dictionary.

    Args:
        config_paths: Configuration paths dict, or 'auto' to initialize
        options: Command-line options to override defaults

    Returns:
        Complete settings dict
    """
    if config_paths == 'auto':
        from .config import init_config_paths
        config_paths = init_config_paths()
    # ...
```

**Benefits**: Explicit intention, clearer API, easier to test

---

**Issue**: Tight coupling to ct and pil modules
**Principle**: Dependency Inversion (SOLID)
**Location**: Lines 22-23 (imports)
**Problem**: Direct imports create tight coupling

**Suggested Improvement**:
```python
def create_settings(config_paths=None, options=None,
                   default_extensions=None, user_path=None):
    """Create settings with injectable dependencies."""
    if default_extensions is None:
        from .pil import IMAGE_READ_EXTENSIONS
        default_extensions = IMAGE_READ_EXTENSIONS
    if user_path is None:
        from . import ct
        user_path = ct.USER_PATH

    settings = {
        'extensions': default_extensions,
        # ...
        'droplet_path': user_path,
        'paths': [user_path],
    }
    # ...
```

**Benefits**: Easier to test with mocks, clearer dependencies, less coupling

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

### phatch/core/safeGlobals.py

⚠️ **CRITICAL SECURITY ISSUE** ⚠️

**Issue**: Attempting to create "safe" namespace for eval() - NOT ACTUALLY SECURE
**Principle**: Security by Design, KISS
**Location**: Entire module
**Problem**: Using plain dict with filtered builtins to create "safe" globals for eval() is fundamentally insecure

**Why This Is Dangerous**:
1. **Trivial to bypass**: Attackers can access builtins through object introspection
   ```python
   # Example attack through "safe" globals:
   eval("''.__class__.__bases__[0].__subclasses__()", safe_globals())
   # Returns all classes, including file I/O, subprocess, etc.
   ```

2. **False sense of security**: Filtering `_` prefixed names doesn't prevent access
   - Can still get `__import__` through `().__class__.__bases__[0].__subclasses__()`
   - Can access `open()`, `exec()`, `compile()`, etc.

3. **Cannot be fixed**: No way to make eval() with plain dict truly safe in Python

**Current Usage**:
- Used for evaluating user expressions (filename patterns like `<width>x<height>`)
- Provides math, random, and now() functions for expressions

**Edge Case Bugs Found**:
- `allow('')` raises IndexError for empty string (line 30)
- Should handle edge cases even if refactoring

**Suggested Improvements** (HIGH PRIORITY):

**Option 1: Template Engine (RECOMMENDED)**
```python
from string import Template

# For simple substitution:
template = Template('${width}x${height}')
result = template.substitute(width=1920, height=1080)

# Or use Jinja2 for more complex cases:
from jinja2 import Environment, select_autoescape

env = Environment(autoescape=select_autoescape())
template = env.from_string('{{width}}x{{height}}')
result = template.render(width=1920, height=1080)
```

**Option 2: AST-based Safe Evaluation**
```python
import ast
import operator

class SafeExpressionEvaluator:
    """Safely evaluate mathematical expressions using AST."""

    ALLOWED_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        # ... other safe operations
    }

    ALLOWED_FUNCS = {
        'sqrt': math.sqrt,
        'sin': math.sin,
        # ... other safe functions
    }

    def eval(self, expr, variables):
        """Evaluate expression safely."""
        tree = ast.parse(expr, mode='eval')
        return self._eval_node(tree.body, variables)

    def _eval_node(self, node, variables):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            elif node.id in self.ALLOWED_FUNCS:
                return self.ALLOWED_FUNCS[node.id]
            else:
                raise ValueError(f"Unknown variable: {node.id}")
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in self.ALLOWED_OPS:
                raise ValueError(f"Disallowed operation: {type(node.op)}")
            left = self._eval_node(node.left, variables)
            right = self._eval_node(node.right, variables)
            return self.ALLOWED_OPS[type(node.op)](left, right)
        # ... handle other node types
        else:
            raise ValueError(f"Disallowed expression type: {type(node)}")
```

**Option 3: RestrictedPython (if complex logic needed)**
```python
from RestrictedPython import compile_restricted, safe_globals

# More secure than plain dict, but still has limitations
code = compile_restricted(user_expression, '<string>', 'eval')
result = eval(code, safe_globals)
```

**Option 4: Custom DSL Parser (MOST SECURE)**
```python
import pyparsing as pp

class PatternParser:
    """Parse filename patterns without eval()."""

    def __init__(self):
        # Define grammar for allowed patterns
        self.variable = pp.Word(pp.alphas + '_')
        self.pattern = pp.Combine(
            pp.Literal('<') + self.variable + pp.Literal('>')
        )

    def parse(self, pattern, variables):
        """Parse and substitute pattern safely."""
        # Parse pattern, substitute variables
        # No eval() needed!
```

**Migration Path**:
1. Audit all uses of safeGlobals.safe_globals() in codebase
2. Categorize expressions by complexity (simple substitution vs math expressions)
3. Migrate simple cases to Template/Jinja2 first (low risk)
4. Migrate math expressions to AST evaluator or custom parser
5. Keep comprehensive tests as regression suite
6. Remove safeGlobals.py entirely

**Benefits**:
- Actually secure (no eval() bypass)
- Clearer intent (template vs expression evaluation)
- Easier to extend (add new variables/functions safely)
- Better error messages (parse errors vs runtime exceptions)
- Performance improvement (no eval() overhead)

**Testing Strategy During Migration**:
- Keep current tests as "legacy behavior" suite
- Add parallel tests for new implementation
- Run both test suites during migration
- Remove legacy tests only after full migration

---

### phatch/core/preview.py

**Issue**: Pillow API compatibility - Image.ANTIALIAS deprecated
**Principle**: KISS, Future-proofing
**Location**: Lines 40, 49 (FIXED), and many other files
**Problem**: Used deprecated `Image.ANTIALIAS` constant which was removed in Pillow 10+

**Fix Applied**:
```python
# Changed from:
source_image.thumbnail(size, Image.ANTIALIAS)

# To:
source_image.thumbnail(size, Image.LANCZOS)
```

**Broader Issue**: This same problem exists in multiple files:
- `phatch/lib/thumbnail.py` (3 occurrences)
- `phatch/actions/round.py` (1 occurrence)
- `phatch/actions/grid.py` (1 occurrence)
- `phatch/actions/contour.py` (2 occurrences)
- `phatch/other/tamogen.py` (1 occurrence)
- `phatch/core/pil.py` (1 occurrence)

**Suggested Improvement**: Create a compatibility constant at module level
```python
# In phatch/core/pil.py or phatch/lib/imtools.py:
from PIL import Image

# Compatibility for Pillow 10+
RESAMPLING_FILTER = getattr(Image, 'LANCZOS', None) or Image.Resampling.LANCZOS

# Then use throughout codebase:
image.thumbnail(size, RESAMPLING_FILTER)
```

**Benefits**: Single point of compatibility handling, easier future upgrades

---

**Issue**: Duplicated calculation in thumbnail sizing
**Principle**: DRY (Don't Repeat Yourself)
**Location**: Lines 38-39
**Problem**:
```python
source_image.thumbnail(
    (min(source_image.size[0], size[0] * 1),
    min(source_image.size[0], size[0] * 1)),  # Same calculation twice
    Image.LANCZOS)
```

**Suggested Improvement**:
```python
# Should likely be:
max_width = min(source_image.size[0], size[0])
max_height = min(source_image.size[1], size[1])
source_image.thumbnail((max_width, max_height), Image.LANCZOS)
```

**Note**: The current code uses `size[0]` for both width AND height calculation. This appears to be a bug - should use `size[1]` for height.

---

**Issue**: Tight coupling to api.ACTIONS global
**Principle**: Dependency Inversion (SOLID)
**Location**: Line 42
**Problem**: Direct dependency on global `api.ACTIONS` dict makes testing difficult

**Suggested Improvement**:
```python
def generate(source, size=(48, 48), path=USER_PREVIEW_PATH, force=True,
             actions=None):
    """Generate preview thumbnails for actions.

    Args:
        actions: Dict of action classes. If None, uses api.ACTIONS.
    """
    if actions is None:
        actions = api.ACTIONS

    # ... rest of function uses actions parameter
```

**Benefits**: Easier to test, more flexible, follows dependency injection

---

**Issue**: Hardcoded file extension
**Principle**: KISS, Don't hardcode configuration
**Location**: Line 44
**Problem**: Always saves as `.png` regardless of source format

**Suggested Improvement**:
```python
def generate(source, size=(48, 48), path=USER_PREVIEW_PATH, force=True,
             output_format='png'):
    # ...
    filename = os.path.join(path, f"{action.label}.{output_format}")
```

**Benefits**: More flexible, could support other formats if needed

---

**Issue**: No error handling
**Principle**: Robustness, KISS
**Location**: Entire function
**Problem**: No try/except for image operations that could fail

**Suggested Improvement**:
```python
def generate(source, size=(48, 48), path=USER_PREVIEW_PATH, force=True):
    try:
        source_image = openImage.open(source)
    except Exception as e:
        print(f"Failed to open source image {source}: {e}")
        return

    # ... rest with appropriate error handling
```

**Benefits**: More robust, better user experience, easier debugging

---

### phatch/actions/*.py (39 files)

✅ **FIXED - PYTHON 2 → 3 MIGRATION ISSUE** ✅

**Issue**: Old PIL import syntax preventing Pillow 3+ compatibility
**Principle**: Future-proofing, KISS
**Location**: 39 action files in `phatch/actions/`
**Problem**: Actions use Python 2 era `import Image` instead of `from PIL import Image`

**Example** (from invert.py):
```python
# INCORRECT (Python 2 / old PIL):
def init():
    global Image, ImageChops, imtools
    import Image          # ❌ ModuleNotFoundError in Pillow
    import ImageChops     # ❌ ModuleNotFoundError in Pillow
    from lib import imtools

# CORRECT (Python 3 / Pillow 3+):
def init():
    global Image, ImageChops, imtools
    from PIL import Image, ImageChops  # ✅ Works with Pillow
    from lib import imtools
```

**Impact**:
- **BLOCKS ACTION TESTING**: Cannot import and test any affected actions
- **RUNTIME FAILURES**: Actions fail at runtime when called
- **AFFECTS 71% OF ACTIONS**: 39 out of 55 action modules

**Affected Actions**:
All actions that import PIL modules in their `init()` function need fixing.

**Fix Pattern**:
```bash
# Search pattern:
grep -l "import Image$" phatch/actions/*.py

# Replace:
import Image → from PIL import Image
import ImageOps → from PIL import ImageOps
import ImageChops → from PIL import ImageChops
import ImageDraw → from PIL import ImageDraw
import ImageFilter → from PIL import ImageFilter
import ImageFont → from PIL import ImageFont
import ImageEnhance → from PIL import ImageEnhance
```

**Migration Strategy**:
1. **Option A: Automated Fix** (RECOMMENDED)
   ```python
   # Script to fix all at once
   import os
   import re

   for filename in os.listdir('phatch/actions/'):
       if not filename.endswith('.py'):
           continue
       filepath = os.path.join('phatch/actions/', filename)
       with open(filepath, 'r') as f:
           content = f.read()

       # Replace old PIL imports
       replacements = {
           r'    import Image\n': '    from PIL import Image\n',
           r'    import ImageOps\n': '    from PIL import ImageOps\n',
           # ... etc
       }
       for old, new in replacements.items():
           content = re.sub(old, new, content)

       with open(filepath, 'w') as f:
           f.write(content)
   ```

2. **Option B: Incremental Fix**
   - Fix actions as tests are written (current approach)
   - Pros: Test-driven, careful
   - Cons: Slow, many files

**Recommended**: Option A - Automated bulk fix, then run all tests

**Benefits**:
- Unblocks action testing phase
- Fixes runtime errors
- Modernizes codebase
- Single point in time fix

**Testing Strategy**:
- Fix one action, write tests, verify pattern works
- Apply bulk fix to all actions
- Run existing tests to ensure no regressions
- Write tests for remaining actions

**Status**:
- ✅ **COMPLETED**: All 39 files fixed with automated script
- ✅ Fixed 76 import statements across all action files
- ✅ All tests passing (235 tests)
- ✅ All action modules now importable and testable

**Fix Applied** (2025-10-09):
Used automated script `tests/scripts/fix_pil_imports.py` to bulk fix all affected files.
Script features:
- DRY-run mode for safe preview
- Groups consecutive imports for cleaner output
- Comprehensive error handling
- Follows SOLID, DRY, KISS principles

**Result**: ⚠️ CRITICAL blocker removed - Phase 2 action testing fully unblocked

---

## Priority Refactorings

Based on impact and feasibility:

1. ⚠️ **CRITICAL**: Replace safeGlobals with secure alternative (template engine/AST parser) - SECURITY ISSUE
2. ✅ **COMPLETED**: Fix PIL import syntax in 39 action files (Python 2 → 3 migration)
3. **HIGH**: Fix Pillow Image.ANTIALIAS compatibility across codebase (8 files) - breaks on Pillow 10+
4. **HIGH**: Extract ConfigPaths class (config.py) - improves testability significantly
5. **HIGH**: Split init_config_paths() into smaller functions - easier to understand and test
6. **MEDIUM**: Fix preview.py thumbnail calculation bug (uses width for both dimensions)
7. **MEDIUM**: Add ABC/Protocol for Receiver classes - clearer contracts
8. **MEDIUM**: Remove disabled code blocks - reduces confusion
9. **MEDIUM**: Refactor settings.py to use SettingsBuilder pattern
10. **LOW**: Standardize imports - long-term maintainability

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

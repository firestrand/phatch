# Phatch Test Suite

This directory contains the test suite for Phatch (PHoto bATCH Processor) on supported CPython 3.11-3.13 releases.

## Quick Start

```bash
# Install the locked project, GUI support, and development tools
uv sync --locked --dev --extra gui

# Run the full canonical GUI-enabled gate with 90% coverage enforcement
uv run --extra gui python scripts/verify.py

# Run only the partial headless suite without making a coverage claim
uv run pytest --no-cov --ignore=tests/unit/pywx \
  --ignore=tests/integration/test_gui_smoke.py \
  --ignore=tests/integration/test_windows_gui_runtime.py

# Run specific test file
pytest tests/quality/test_code_quality.py

# Run tests by marker
pytest -m "not slow"  # Skip slow tests
```

## Test Organization

### Directory Structure

Tests are now organized following modern best practices:

- **`unit/`** - Unit tests for individual functions/classes
  - `unit/actions/` - Tests for phatch/actions/
  - `unit/core/` - Tests for phatch/core/
  - `unit/lib/` - Tests for phatch/lib/
  - `unit/console/` - Tests for phatch/console/

- **`integration/`** - Integration tests for component interactions
  - Test action pipelines
  - Test file I/O operations
  - Test metadata operations

- **`functional/`** - End-to-end functional/acceptance tests
  - Test complete workflows
  - Test with real images and actionlists

- **`quality/`** - Code quality and standards tests
  - `quality/test_code_quality.py` - Code quality checks using ruff
  - `quality/test_doctests.py` - Doctest runner
  - `quality/test_license.py` - License header validation (optional)

### Legacy Test Files

- **`acceptance_test.py`** - Legacy acceptance tests (will be migrated to functional/)
- **`test_suite/`** - Acceptance test utilities and configuration

### Test Data

- **`input/`** - Sample images for testing (bee.png, frog.gif, etc.)
- **`output/`** - Generated test output (gitignored, created during test runs)

### Configuration Files

- **`conftest.py`** - Pytest configuration and shared fixtures
- **`pyproject.toml`** - Pytest, coverage, Ruff, and ty configuration
- **`PYTHON3_MIGRATION_PLAN.md`** - Detailed migration documentation

## Running Tests

### All Tests

```bash
# From the project root; native GUI tests are scripted and require no human input
uv run --extra gui python scripts/verify.py
```

The canonical local gate includes the GUI suite and enforces 90% line, branch,
and changed-module coverage. The headless command above is intentionally only a
partial test run. CI makes its final coverage judgment after combining all nine
non-GUI OS/Python contributors with the native Windows GUI contributor. Native
Windows execution is still required downstream and is not proven by a local
Linux or macOS run.
Local coverage verification derives its changed-module boundary from Git rather
than treating the configured historical module list as authoritative.

### Specific Test Types

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Functional tests
pytest tests/functional/

# Quality tests
pytest tests/quality/

# Code quality (ruff) - can also run directly
python tests/quality/test_code_quality.py
# or
pytest tests/quality/test_code_quality.py

# Doctests - run directly
python tests/quality/test_doctests.py

# License headers (requires licensecheck command)
pytest tests/quality/test_license.py

# Legacy acceptance tests (will be migrated to functional/)
cd tests
python acceptance_test.py --help  # See options
python acceptance_test.py --tag save --no-execute  # Generate only
python acceptance_test.py --select scale  # Test specific action
```

### Using Test Markers

Tests are marked for easy filtering:

```bash
# Skip slow tests
pytest -m "not slow"

# Run only unit tests
pytest -m unit

# Run only acceptance tests
pytest -m acceptance

# Skip tests requiring external tools
pytest -m "not requires_external"

# Skip tests requiring display/GUI
pytest -m "not requires_display"
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=phatch --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# Terminal coverage report
pytest --cov=phatch --cov-report=term
```

## Test Dependencies

### Required

- **pytest** >=7.0.0 - Test framework
- **pytest-cov** >=4.0.0 - Coverage reporting
- **ruff** >=0.1.0 - Code quality linting

Install all required dependencies:
```bash
uv sync --all-extras --dev
```

### Optional

- **licensecheck** - For license header validation
  - Linux: `sudo apt-get install devscripts`
  - macOS: `brew install devscripts` (or skip test)
  - Test will be skipped if not available

- **pytest-xdist** - Parallel test execution
  ```bash
  pytest -n auto  # Run tests in parallel
  ```

## Adding New Tests

### Unit Tests

1. Create test file following naming convention: `test_*.py` or `*_test.py`
2. Import pytest: `import pytest`
3. Use fixtures from `conftest.py`:
   ```python
   def test_something(project_root, phatch_package_dir):
       # Test implementation
       assert something
   ```
4. Mark tests appropriately:
   ```python
   @pytest.mark.unit
   def test_my_feature():
       pass
   ```

### Acceptance Tests

1. Add action to test in `acceptance_test.py`
2. Or modify `test_suite/defaults.py` for custom defaults
3. Run: `python acceptance_test.py --select <action_name>`

### Doctests

1. Add docstring examples to functions:
   ```python
   def my_function(x):
       """
       Do something with x.

       >>> my_function(2)
       4
       """
       return x * 2
   ```

2. Run: `python tests/doc_test.py`

## Test Markers

Defined in `[tool.pytest.ini_options]` in `../pyproject.toml`:

- **`@pytest.mark.unit`** - Unit tests
- **`@pytest.mark.acceptance`** - Acceptance/integration tests
- **`@pytest.mark.slow`** - Tests that take significant time
- **`@pytest.mark.requires_display`** - Tests needing GUI/display
- **`@pytest.mark.requires_external`** - Tests needing external tools

Usage:
```python
import pytest

@pytest.mark.unit
@pytest.mark.slow
def test_heavy_computation():
    # Test implementation
    pass
```

## Fixtures

Available fixtures (from `conftest.py`):

- **`project_root`** - Path to project root directory
- **`tests_dir`** - Path to tests directory
- **`phatch_package_dir`** - Path to phatch package
- **`test_input_dir`** - Path to tests/input (sample images)
- **`test_output_dir`** - Path to tests/output

Example:
```python
def test_sample_images(test_input_dir):
    images = list(test_input_dir.glob("*.png"))
    assert len(images) > 0
```

## Troubleshooting

### Import Errors

If you get `ModuleNotFoundError: No module named 'phatch'`:

- Ensure you're running from project root: `pytest` (not `cd tests && pytest`)
- Or run from tests directory with proper PYTHONPATH:
  ```bash
  cd tests
  PYTHONPATH=.. pytest
  ```

### Acceptance Test Errors

If acceptance tests fail with import errors:

- Verify `bin/phatch` works: `python bin/phatch --help`
- Check `test_suite/config.py` has correct paths
- Ensure project root is in sys.path

### License Test Skipped

If license test is skipped:

- Install licensecheck: `brew install devscripts` (macOS) or `sudo apt-get install devscripts` (Linux)
- Or ignore: test is optional and will skip gracefully

### Code Quality Test Failures

If code quality test finds violations:

```bash
# View violations
python tests/quality/test_code_quality.py

# Auto-fix many issues
ruff check --fix .

# Configure ignored rules in pyproject.toml
```

## Test Output

Test output is written to `tests/output/` (gitignored):

- **`output/images/`** - Processed test images
- **`output/actionlists/`** - Generated action lists
- **`output/logs.txt`** - Test execution logs
- **`output/report.txt`** - Test reports

Clean output:
```bash
cd tests
python acceptance_test.py --clean
```

## Continuous Integration

For CI environments:

```bash
# Install all locked dependencies including optional ones
uv sync --all-extras --dev
# If on Linux:
sudo apt-get install -y devscripts

# Run the complete repository gate
uv run python scripts/verify.py --base-ref origin/master
```

## Migration Notes

This test suite was fully migrated from Python 2 to Python 3 in October 2025. See `PYTHON3_MIGRATION_PLAN.md` for complete migration details.

Key changes:
- Replaced `nosetests` with `pytest`
- Replaced bundled `pep8.py` with modern `ruff` linter
- Fixed import paths to use phatch package (not module)
- Made license test optional (requires external tool)
- Added pytest markers for test organization

## Contributing

When adding tests:

1. Follow existing patterns and use shared fixtures
2. Add appropriate markers (`@pytest.mark.unit`, etc.)
3. Update this README if adding new test types
4. Ensure tests pass: `pytest`
5. Check code quality: `python tests/quality/test_code_quality.py`

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [ruff documentation](https://docs.astral.sh/ruff/)
- [Phatch project](https://github.com/firestrand/phatch)

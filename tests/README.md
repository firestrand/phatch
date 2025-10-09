# Phatch Test Suite

This directory contains the test suite for Phatch (PHoto bATCH Processor), fully migrated to Python 3.12+.

## Quick Start

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run tests with coverage
pytest --cov=phatch --cov-report=html

# Run specific test file
pytest tests/pep8_test.py

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
  - `quality/test_pep8.py` - PEP8 compliance using ruff
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
- **`pytest.ini`** - Pytest settings, markers, and test discovery patterns
- **`PYTHON3_MIGRATION_PLAN.md`** - Detailed migration documentation

## Running Tests

### All Tests

```bash
# From project root
pytest

# From tests directory
cd tests
pytest
```

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

# Code quality (PEP8) - can also run directly
python tests/quality/test_pep8.py
# or
pytest tests/quality/test_pep8.py

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
pip install -r requirements-dev.txt
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

Defined in `pytest.ini`:

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

### PEP8 Test Failures

If PEP8 test finds violations:

```bash
# View violations
python tests/pep8_test.py

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
# Install all dependencies including optional ones
pip install -r requirements-dev.txt
# If on Linux:
sudo apt-get install -y devscripts

# Run full test suite
pytest --cov=phatch --cov-report=xml

# Check code quality
python tests/pep8_test.py
```

## Migration Notes

This test suite was fully migrated from Python 2 to Python 3 in October 2025. See `PYTHON3_MIGRATION_PLAN.md` for complete migration details.

Key changes:
- Replaced `nosetests` with `pytest`
- Replaced bundled `pep8.py` with `ruff`
- Fixed import paths to use phatch package (not module)
- Made license test optional (requires external tool)
- Added pytest markers for test organization

## Contributing

When adding tests:

1. Follow existing patterns and use shared fixtures
2. Add appropriate markers (`@pytest.mark.unit`, etc.)
3. Update this README if adding new test types
4. Ensure tests pass: `pytest`
5. Check code quality: `python tests/pep8_test.py`

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [ruff documentation](https://docs.astral.sh/ruff/)
- [Phatch project](https://github.com/firestrand/phatch)

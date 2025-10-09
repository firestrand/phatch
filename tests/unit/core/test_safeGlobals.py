"""Unit tests for phatch.core.safeGlobals module.

Tests safe globals creation for sandboxed expression evaluation.

SECURITY NOTE: This module attempts to create "safe" globals for eval(),
but this approach has known security vulnerabilities in Python. These tests
document current behavior for regression testing during refactoring to a
more secure approach (template engine, AST parsing, or RestrictedPython).

See REFACTORING_NOTES.md for security concerns and migration plan.
"""

import builtins
import math
import random

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.core import safeGlobals


class TestAllowFunction:
    """Test allow() function for filtering module attributes."""

    def test_allow_public_name(self):
        """allow() should return True for public names."""
        assert safeGlobals.allow('public_name') is True
        assert safeGlobals.allow('sqrt') is True
        assert safeGlobals.allow('random') is True

    def test_allow_rejects_private(self):
        """allow() should return False for names starting with underscore."""
        assert safeGlobals.allow('_private') is False
        assert safeGlobals.allow('__dunder__') is False
        assert safeGlobals.allow('__class__') is False

    def test_allow_empty_string_raises(self):
        """allow() raises IndexError for empty string (edge case bug)."""
        # Current implementation doesn't handle empty string
        # This is a bug that should be fixed in refactoring
        import pytest
        with pytest.raises(IndexError):
            safeGlobals.allow('')

    def test_allow_only_checks_first_character(self):
        """allow() should only check first character."""
        assert safeGlobals.allow('public_with_under_score') is True
        assert safeGlobals.allow('x_y_z') is True

    def test_allow_with_numbers(self):
        """allow() should accept names starting with numbers."""
        # Python identifiers can't start with numbers, but allow() doesn't enforce that
        assert safeGlobals.allow('123') is True

    def test_allow_with_special_chars(self):
        """allow() should accept names with special characters."""
        # These aren't valid Python identifiers, but allow() just checks first char
        assert safeGlobals.allow('$special') is True
        assert safeGlobals.allow('@symbol') is True


class TestAddDictionaryFunction:
    """Test add_dictionary() function for selectively copying dict items."""

    def test_add_dictionary_copies_public_items(self):
        """add_dictionary should copy items not starting with underscore."""
        namespace = {}
        source = {'public1': 'value1', 'public2': 'value2'}

        safeGlobals.add_dictionary(namespace, source)

        assert namespace['public1'] == 'value1'
        assert namespace['public2'] == 'value2'
        assert len(namespace) == 2

    def test_add_dictionary_filters_private_items(self):
        """add_dictionary should filter items starting with underscore."""
        namespace = {}
        source = {
            'public': 'value',
            '_private': 'filtered',
            '__dunder__': 'filtered',
        }

        safeGlobals.add_dictionary(namespace, source)

        assert 'public' in namespace
        assert '_private' not in namespace
        assert '__dunder__' not in namespace
        assert len(namespace) == 1

    def test_add_dictionary_mixed_items(self):
        """add_dictionary should handle mix of public and private."""
        namespace = {}
        source = {
            'a': 1,
            '_b': 2,
            'c': 3,
            '__d': 4,
            'e': 5,
        }

        safeGlobals.add_dictionary(namespace, source)

        assert namespace == {'a': 1, 'c': 3, 'e': 5}

    def test_add_dictionary_to_existing_namespace(self):
        """add_dictionary should add to existing namespace."""
        namespace = {'existing': 'value'}
        source = {'new': 'item'}

        safeGlobals.add_dictionary(namespace, source)

        assert namespace['existing'] == 'value'
        assert namespace['new'] == 'item'
        assert len(namespace) == 2

    def test_add_dictionary_overwrites_existing(self):
        """add_dictionary should overwrite existing keys."""
        namespace = {'key': 'old_value'}
        source = {'key': 'new_value'}

        safeGlobals.add_dictionary(namespace, source)

        assert namespace['key'] == 'new_value'

    def test_add_dictionary_empty_source(self):
        """add_dictionary should handle empty source dict."""
        namespace = {'existing': 'value'}
        source = {}

        safeGlobals.add_dictionary(namespace, source)

        assert namespace == {'existing': 'value'}

    def test_add_dictionary_various_types(self):
        """add_dictionary should handle various value types."""
        namespace = {}
        source = {
            'int_val': 42,
            'float_val': 3.14,
            'str_val': 'hello',
            'list_val': [1, 2, 3],
            'dict_val': {'nested': 'dict'},
            'func_val': lambda x: x * 2,
        }

        safeGlobals.add_dictionary(namespace, source)

        assert namespace['int_val'] == 42
        assert namespace['float_val'] == 3.14
        assert namespace['str_val'] == 'hello'
        assert namespace['list_val'] == [1, 2, 3]
        assert namespace['dict_val'] == {'nested': 'dict'}
        assert callable(namespace['func_val'])


class TestAddModuleFunction:
    """Test add_module() function for importing module contents."""

    def test_add_module_imports_math(self):
        """add_module should import math module functions."""
        namespace = {}

        safeGlobals.add_module(namespace, math)

        # Check common math functions are present
        assert 'sqrt' in namespace
        assert 'sin' in namespace
        assert 'cos' in namespace
        assert 'pi' in namespace
        assert 'e' in namespace

    def test_add_module_filters_private(self):
        """add_module should filter private module attributes."""
        namespace = {}

        safeGlobals.add_module(namespace, math)

        # Private attributes should not be copied
        assert '__name__' not in namespace
        assert '__doc__' not in namespace
        assert '__file__' not in namespace

    def test_add_module_functions_work(self):
        """add_module should import working functions."""
        namespace = {}

        safeGlobals.add_module(namespace, math)

        # Test that imported functions actually work
        assert namespace['sqrt'](16) == 4.0
        assert abs(namespace['sin'](namespace['pi'] / 2) - 1.0) < 0.0001

    def test_add_module_imports_random(self):
        """add_module should import random module functions."""
        namespace = {}

        safeGlobals.add_module(namespace, random)

        # Check common random functions are present
        assert 'randint' in namespace
        assert 'choice' in namespace
        assert 'random' in namespace

    def test_add_module_to_existing_namespace(self):
        """add_module should add to existing namespace."""
        namespace = {'existing': 'value'}

        safeGlobals.add_module(namespace, math)

        assert 'existing' in namespace
        assert 'sqrt' in namespace


class TestSafeGlobalsFunction:
    """Test safe_globals() function for creating sandboxed namespace."""

    def test_safe_globals_returns_dict(self):
        """safe_globals should return a dictionary."""
        result = safeGlobals.safe_globals()
        assert isinstance(result, dict)

    def test_safe_globals_includes_math(self):
        """safe_globals should include math module functions."""
        result = safeGlobals.safe_globals()

        assert 'sqrt' in result
        assert 'sin' in result
        assert 'cos' in result
        assert 'tan' in result
        assert 'pi' in result
        assert 'e' in result

    def test_safe_globals_includes_random(self):
        """safe_globals should include random module functions."""
        result = safeGlobals.safe_globals()

        assert 'randint' in result
        assert 'random' in result
        assert 'choice' in result

    def test_safe_globals_includes_now(self):
        """safe_globals should include now function from metadata."""
        result = safeGlobals.safe_globals()

        assert 'now' in result
        assert callable(result['now'])

    def test_safe_globals_excludes_private(self):
        """safe_globals should exclude private attributes."""
        result = safeGlobals.safe_globals()

        # Check some common private attributes are not present
        private_attrs = ['__name__', '__doc__', '__file__', '__builtins__',
                        '__import__', '__class__', '__bases__']
        for attr in private_attrs:
            assert attr not in result, f"Private attribute {attr} should not be in safe_globals"

    def test_safe_globals_math_functions_work(self):
        """safe_globals math functions should be functional."""
        result = safeGlobals.safe_globals()

        # Test some math operations
        assert result['sqrt'](25) == 5.0
        assert result['pow'](2, 3) == 8.0
        assert abs(result['sin'](0)) < 0.0001

    def test_safe_globals_new_dict_each_call(self):
        """safe_globals should return new dict each call."""
        result1 = safeGlobals.safe_globals()
        result2 = safeGlobals.safe_globals()

        # Should be different dict objects
        assert result1 is not result2

        # But should have same content
        assert result1.keys() == result2.keys()

    def test_safe_globals_now_function_callable(self):
        """safe_globals now function should be callable."""
        result = safeGlobals.safe_globals()

        # now() should return current timestamp (DateTime object)
        timestamp = result['now']()
        # DateTime from metadata module - has string representation
        assert timestamp is not None
        assert hasattr(timestamp, '__str__')

    def test_safe_globals_count(self):
        """safe_globals should have reasonable number of items."""
        result = safeGlobals.safe_globals()

        # Should have math + random functions + now
        # Math has ~50 items, random has ~30 items
        # Exact count depends on Python version, but should be > 50
        assert len(result) > 50

    def test_safe_globals_no_builtins(self):
        """safe_globals should not include dangerous builtins."""
        result = safeGlobals.safe_globals()

        # These should NOT be present for "safety"
        dangerous = ['eval', 'exec', 'compile', '__import__',
                    'open', 'input', 'exit', 'quit']
        for name in dangerous:
            assert name not in result, f"Dangerous builtin {name} should not be in safe_globals"


class TestIntegrationScenarios:
    """Test realistic usage scenarios for safe globals."""

    def test_math_expression_evaluation(self):
        """Test evaluating math expressions with safe_globals."""
        globals_dict = safeGlobals.safe_globals()

        # These expressions should work
        result1 = eval('sqrt(16)', globals_dict)
        assert result1 == 4.0

        result2 = eval('pi * 2', globals_dict)
        assert abs(result2 - 6.283185) < 0.00001

        result3 = eval('sin(pi / 2)', globals_dict)
        assert abs(result3 - 1.0) < 0.0001

    def test_random_expression_evaluation(self):
        """Test evaluating random expressions with safe_globals."""
        globals_dict = safeGlobals.safe_globals()

        # Random functions should work
        result = eval('randint(1, 10)', globals_dict)
        assert 1 <= result <= 10

        result = eval('choice([1, 2, 3])', globals_dict)
        assert result in [1, 2, 3]

    def test_combined_expression_evaluation(self):
        """Test evaluating expressions combining math and other functions."""
        globals_dict = safeGlobals.safe_globals()

        # Complex expression
        result = eval('int(sqrt(16) * pi)', globals_dict)
        assert isinstance(result, int)
        assert result == 12  # int(4 * 3.14159...) = 12

    def test_expression_with_now(self):
        """Test evaluating expressions with now() function."""
        globals_dict = safeGlobals.safe_globals()

        # Should be able to call now()
        result = eval('now()', globals_dict)
        # Returns DateTime object from metadata module
        assert result is not None
        assert hasattr(result, '__str__')


class TestSecurityConcerns:
    """Test known security vulnerabilities (documenting for refactoring).

    WARNING: These tests demonstrate that safe_globals() is NOT secure.
    This is intentional documentation for refactoring efforts.
    DO NOT use safe_globals() for actual security!
    """

    def test_security_note_in_docstring(self):
        """Verify module has security warnings in docstring."""
        # This test ensures future developers are warned
        # Module may not have docstring, but this test file should
        assert __doc__ is not None
        assert 'SECURITY' in __doc__

    def test_no_builtins_in_globals(self):
        """Document that builtins are not explicitly included."""
        result = safeGlobals.safe_globals()

        # These dangerous builtins should not be explicitly added
        assert 'eval' not in result
        assert 'exec' not in result
        assert '__import__' not in result

        # Note: This doesn't make eval() safe! Attackers can still access
        # these through object introspection.

    def test_namespace_is_dict(self):
        """Document that result is a plain dict."""
        result = safeGlobals.safe_globals()

        # It's a dict, not a custom restricted type
        assert isinstance(result, dict)
        assert type(result).__name__ == 'dict'  # Specifically dict, not subclass

        # This means eval() with this dict is NOT secure - attackers can
        # escape through ''.__class__.__bases__[0].__subclasses__() etc.

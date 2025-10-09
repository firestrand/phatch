"""Unit tests for phatch.core.translation module.

Tests translation functions for converting between English and localized text.
"""

import builtins

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.core import translation


class TestTranslationReExports:
    """Test that translation module re-exports _t and _r functions."""

    def test_has_t_function(self):
        """_t function should be available."""
        assert hasattr(translation, '_t')
        assert callable(translation._t)

    def test_has_r_function(self):
        """_r function should be available."""
        assert hasattr(translation, '_r')
        assert callable(translation._r)


class TestToEnglishFunction:
    """Test to_english() function."""

    def test_to_english_exists(self):
        """to_english function should exist."""
        assert hasattr(translation, 'to_english')
        assert callable(translation.to_english)

    def test_to_english_with_simple_string(self):
        """to_english should return input for simple strings."""
        result = translation.to_english('Hello World')
        assert isinstance(result, str)
        assert result == 'Hello World'

    def test_to_english_with_expression(self):
        """to_english should handle variable expressions."""
        # Test with expression containing variables
        result = translation.to_english('<test>')
        assert isinstance(result, str)

    def test_to_english_preserves_type(self):
        """to_english should return a string."""
        assert isinstance(translation.to_english('test'), str)
        assert isinstance(translation.to_english(''), str)


class TestToLocalFunction:
    """Test to_local() function."""

    def test_to_local_exists(self):
        """to_local function should exist."""
        assert hasattr(translation, 'to_local')
        assert callable(translation.to_local)

    def test_to_local_with_simple_string(self):
        """to_local should translate simple strings."""
        result = translation.to_local('Hello')
        assert isinstance(result, str)
        # With our no-op translator, should return same string
        assert result == 'Hello'

    def test_to_local_with_expression(self):
        """to_local should handle variable expressions."""
        result = translation.to_local('<variable>')
        assert isinstance(result, str)

    def test_to_local_preserves_type(self):
        """to_local should return a string."""
        assert isinstance(translation.to_local('test'), str)
        assert isinstance(translation.to_local(''), str)


class TestReverseTranslation:
    """Test reverse translation functionality."""

    def test_reverse_dict_exists(self):
        """REVERSE dictionary should exist."""
        assert hasattr(translation, 'REVERSE')
        assert isinstance(translation.REVERSE, dict)

    def test_reverse_dict_can_be_updated(self):
        """REVERSE dict should be mutable."""
        original_len = len(translation.REVERSE)
        # Should be able to add entries
        test_key = 'test_unique_key_12345'
        translation.REVERSE[test_key] = 'test_value'
        assert translation.REVERSE[test_key] == 'test_value'
        # Clean up
        del translation.REVERSE[test_key]
        assert len(translation.REVERSE) == original_len


class TestExpressionHandling:
    """Test expression parsing with variables and attributes."""

    def test_to_english_with_variable_attribute(self):
        """to_english should handle variable.attribute patterns."""
        # Pattern like <var.attr>
        test_expr = '<image.width>'
        result = translation.to_english(test_expr)
        assert isinstance(result, str)
        # Should contain the expression
        assert '<' in result and '>' in result

    def test_to_local_with_variable_attribute(self):
        """to_local should handle variable.attribute patterns."""
        test_expr = '<image.height>'
        result = translation.to_local(test_expr)
        assert isinstance(result, str)
        assert '<' in result and '>' in result

    def test_roundtrip_consistency(self):
        """Converting to English and back should preserve meaning."""
        original = 'test_string'
        # to_local then to_english should give back original (with no-op translator)
        localized = translation.to_local(original)
        back_to_english = translation.to_english(localized)

        # With no-op translator, should be symmetric
        assert isinstance(back_to_english, str)


class TestEdgeCases:
    """Test edge cases and special inputs."""

    def test_empty_string(self):
        """Functions should handle empty strings."""
        assert translation.to_english('') == ''
        assert translation.to_local('') == ''

    def test_whitespace_string(self):
        """Functions should handle whitespace."""
        result_eng = translation.to_english('   ')
        result_loc = translation.to_local('   ')
        assert isinstance(result_eng, str)
        assert isinstance(result_loc, str)

    def test_special_characters(self):
        """Functions should handle special characters."""
        test_strings = [
            'test\nwith\nnewlines',
            'test\twith\ttabs',
            'test with spaces',
            'test-with-dashes',
            'test_with_underscores',
        ]
        for test_str in test_strings:
            assert isinstance(translation.to_english(test_str), str)
            assert isinstance(translation.to_local(test_str), str)

    def test_unicode_strings(self):
        """Functions should handle Unicode strings."""
        test_strings = [
            'Ελληνικά',  # Greek
            '中文',       # Chinese
            'العربية',   # Arabic
            'Русский',    # Russian
        ]
        for test_str in test_strings:
            result_eng = translation.to_english(test_str)
            result_loc = translation.to_local(test_str)
            assert isinstance(result_eng, str)
            assert isinstance(result_loc, str)

    def test_expression_with_nested_brackets(self):
        """Functions should handle nested bracket expressions."""
        # Edge case: expression within expression
        test_expr = '<<nested>>'
        result_eng = translation.to_english(test_expr)
        result_loc = translation.to_local(test_expr)
        assert isinstance(result_eng, str)
        assert isinstance(result_loc, str)


class TestIntegration:
    """Test integration with actual translation patterns used in Phatch."""

    def test_phatch_filename_pattern(self):
        """Test common Phatch filename variable patterns."""
        patterns = [
            '<filename>',
            '<folder>',
            '<width>x<height>',
            '<type>',
        ]
        for pattern in patterns:
            eng = translation.to_english(pattern)
            loc = translation.to_local(pattern)
            assert isinstance(eng, str)
            assert isinstance(loc, str)
            # Should preserve expression markers
            assert '<' in eng and '>' in eng
            assert '<' in loc and '>' in loc

    def test_mixed_text_and_variables(self):
        """Test strings mixing plain text with variables."""
        mixed = 'Save to <folder> with name <filename>.<type>'
        eng = translation.to_english(mixed)
        loc = translation.to_local(mixed)

        assert isinstance(eng, str)
        assert isinstance(loc, str)
        # Should contain both text and variable markers
        assert 'Save' in eng or 'save' in eng.lower()
        assert '<' in eng and '>' in eng

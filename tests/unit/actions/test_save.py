"""Unit tests for phatch.actions.save module.

Tests the Save action (save and convert images to different formats).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility

Note: This action uses apply() method and requires photo object,
so we focus on metadata, interface, and helper method testing.
"""

import builtins

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import save


class TestSaveAction:
    """Test the Save action class metadata."""

    def test_action_exists(self):
        """Save action class should exist."""
        assert hasattr(save, 'Action')
        assert save.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = save.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = save.Action()
        assert 'save' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(save.Action, 'init')
        assert callable(save.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = save.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_has_apply_method(self):
        """Action should have apply method (not pil)."""
        action = save.Action()
        assert hasattr(action, 'apply')
        assert callable(action.apply)

    def test_action_tags(self):
        """Action should have appropriate tags."""
        action = save.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'file' in tags_lower or 'default' in tags_lower

    def test_action_valid_last(self):
        """Save action should be valid as last action."""
        action = save.Action()
        assert hasattr(action, 'valid_last')
        assert action.valid_last is True


class TestSaveInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_file_name_field(self):
        """interface should define File Name parameter."""
        action = save.Action()
        fields = {}
        action.interface(fields)

        # Should have File Name field
        assert any('file' in k.lower() and 'name' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_as_field(self):
        """interface should define As (type) parameter."""
        action = save.Action()
        fields = {}
        action.interface(fields)

        # Should have As field
        assert 'As' in fields.keys()

    def test_interface_defines_in_field(self):
        """interface should define In (folder) parameter."""
        action = save.Action()
        fields = {}
        action.interface(fields)

        # Should have In field
        assert 'In' in fields.keys()

    def test_interface_defines_resolution_field(self):
        """interface should define Resolution parameter."""
        action = save.Action()
        fields = {}
        action.interface(fields)

        # Should have Resolution field
        assert any('resolution' in k.lower() for k in fields.keys())

    def test_interface_defines_jpeg_quality_field(self):
        """interface should define JPEG Quality parameter."""
        action = save.Action()
        fields = {}
        action.interface(fields)

        # Should have JPEG Quality field
        assert any('jpeg' in k.lower() and 'quality' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_png_optimize_field(self):
        """interface should define PNG Optimize parameter."""
        action = save.Action()
        fields = {}
        action.interface(fields)

        # Should have PNG Optimize field
        assert any('png' in k.lower() and 'optimize' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_metadata_field(self):
        """interface should define Metadata parameter."""
        action = save.Action()
        fields = {}
        action.interface(fields)

        # Should have Metadata field
        assert 'Metadata' in fields.keys()

    def test_interface_defines_tiff_compression_field(self):
        """interface should define TIFF Compression parameter."""
        action = save.Action()
        fields = {}
        action.interface(fields)

        # Should have TIFF Compression field
        assert any('tiff' in k.lower() and 'compression' in k.lower()
                   for k in fields.keys())

    def test_interface_file_name_is_filename_field(self):
        """File Name field should be a FileNameField."""
        action = save.Action()
        fields = {}
        action.interface(fields)

        # Get the File Name field
        filename_field = None
        for key, value in fields.items():
            if 'file' in key.lower() and 'name' in key.lower():
                filename_field = value
                break

        assert filename_field is not None
        assert type(filename_field).__name__ == 'FileNameField'

    def test_interface_jpeg_quality_is_slider(self):
        """JPEG Quality field should be a SliderField."""
        action = save.Action()
        fields = {}
        action.interface(fields)

        # Get the JPEG Quality field
        quality_field = None
        for key, value in fields.items():
            if 'jpeg' in key.lower() and 'quality' in key.lower():
                quality_field = value
                break

        assert quality_field is not None
        assert type(quality_field).__name__ == 'SliderField'

    def test_interface_metadata_is_boolean(self):
        """Metadata field should be a BooleanField."""
        action = save.Action()
        fields = {}
        action.interface(fields)

        # Get the Metadata field
        metadata_field = fields.get('Metadata')

        assert metadata_field is not None
        assert type(metadata_field).__name__ == 'BooleanField'

    def test_interface_has_eleven_fields(self):
        """Save should have eleven parameters."""
        action = save.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 11


class TestSaveHelperMethods:
    """Test helper methods of the Save action."""

    def test_get_format_method_exists(self):
        """get_format method should exist."""
        action = save.Action()
        assert hasattr(action, 'get_format')
        assert callable(action.get_format)

    def test_is_done_info_method_exists(self):
        """is_done_info method should exist."""
        action = save.Action()
        assert hasattr(action, 'is_done_info')
        assert callable(action.is_done_info)

    def test_get_relevant_field_labels_exists(self):
        """get_relevant_field_labels method should exist."""
        action = save.Action()
        assert hasattr(action, 'get_relevant_field_labels')
        assert callable(action.get_relevant_field_labels)

    def test_is_overwrite_existing_images_forced_exists(self):
        """is_overwrite_existing_images_forced method should exist."""
        action = save.Action()
        assert hasattr(action, 'is_overwrite_existing_images_forced')
        assert callable(action.is_overwrite_existing_images_forced)


class TestSaveConstants:
    """Test module-level constants."""

    def test_sizes_constant_exists(self):
        """SIZES constant should exist."""
        assert hasattr(save, 'SIZES')
        assert isinstance(save.SIZES, list)

    def test_tolerances_constant_exists(self):
        """TOLERANCES constant should exist."""
        assert hasattr(save, 'TOLERANCES')
        assert isinstance(save.TOLERANCES, list)

    def test_sizes_has_values(self):
        """SIZES should contain expected values."""
        assert '0' in save.SIZES
        assert '100' in save.SIZES
        assert '1000' in save.SIZES

    def test_tolerances_has_values(self):
        """TOLERANCES should contain expected values."""
        assert '0' in save.TOLERANCES
        assert '10' in save.TOLERANCES
        assert '50' in save.TOLERANCES


class TestSaveIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = save.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = save.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 11

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = save.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'file' in tags_lower or 'default' in tags_lower

    def test_action_docstring_mentions_save(self):
        """Action documentation mentions save or convert."""
        action = save.Action()
        doc_lower = action.__doc__.lower()
        assert 'save' in doc_lower or 'convert' in doc_lower

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        save.init()
        # After init, Image should be available in the module
        assert hasattr(save, 'Image')

    def test_init_loads_imtools(self):
        """init() should load imtools functions."""
        save.init()
        # After init, imtools functions should be available
        assert hasattr(save, 'get_quality')
        assert hasattr(save, 'get_size')
        assert hasattr(save, 'InvalidWriteFormatError')

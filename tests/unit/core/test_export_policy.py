# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Export policy round trips use the real sample with explicit test tags."""

import pytest
from io import BytesIO
from PIL import Image, ImageCms, ImageOps, PngImagePlugin

from phatch.core import api
from phatch.core.batch import run_batch
from phatch.core.export_policy import capture_metadata, prepare_export


@pytest.fixture
def tagged_source(tmp_path, test_input_dir):
    with Image.open(test_input_dir / 'frog.gif') as original:
        image = original.convert('RGB')
    exif = Image.Exif()
    exif[271] = 'Test camera'
    exif[272] = 'Test model'
    exif[315] = 'Test artist'
    exif[274] = 1
    exif[34853] = {1: 'N', 2: (1, 2, 3)}
    exif[34665] = {36867: '2020:01:02 03:04:05', 42033: 'test-device'}
    profile = ImageCms.ImageCmsProfile(
        ImageCms.createProfile('sRGB')
    ).tobytes()
    source = tmp_path / 'tagged.png'
    image.save(source, exif=exif, icc_profile=profile)
    image.close()
    return source


def export(
    source,
    tmp_path,
    policy='preserve',
    color='preserve',
    tags='',
    format='png',
):
    api.import_actions()
    action = api.ACTIONS['Save']()
    action.set_field_as_string('In', str(tmp_path / 'output'))
    action.set_field_as_string('As', format)
    action.set_field_as_string('Metadata Policy', policy)
    action.set_field_as_string('Color Policy', color)
    action.set_field_as_string('Metadata Tags', tags)
    return run_batch([action], [source])


@pytest.mark.parametrize('format', ['jpeg', 'png', 'tiff', 'webp', 'avif'])
@pytest.mark.parametrize(
    'policy', ['preserve', 'strip', 'selected', 'sharing']
)
def test_native_metadata_format_matrix(
    tagged_source, tmp_path, format, policy
):
    Image.init()
    if format.upper() not in Image.SAVE:
        pytest.skip(f'{format} encoder unavailable')
    result = export(
        tagged_source, tmp_path, policy, tags='DateTimeOriginal', format=format
    )
    assert result.status == 'success', result.to_dict(include_details=True)
    with Image.open(result.files[0].outputs[0]) as output:
        output.load()
        exif = output.getexif()
        assert output.info['icc_profile']
        if policy == 'strip':
            # TIFF represents required image structure through IFD/EXIF tags.
            assert not {271, 272, 315, 34665, 34853}.intersection(exif)
            if format != 'tiff':
                assert not exif
        else:
            # AVIF's encoder moves orientation from EXIF to its container.
            assert exif.get(274, 1) == 1
            assert (exif[256], exif[257]) == output.size
            assert exif.get_ifd(34665)[36867] == '2020:01:02 03:04:05'
            assert (271 in exif) == (policy == 'preserve')
            assert (34853 in exif) == (policy == 'preserve')


def test_metadata_preserved_without_optional_backend(tagged_source, tmp_path):
    result = export(tagged_source, tmp_path)
    assert result.status == 'success'
    with Image.open(result.files[0].outputs[0]) as output:
        exif = output.getexif()
        assert exif[271] == 'Test camera'
        assert exif.get_ifd(34665)[36867] == '2020:01:02 03:04:05'
        assert exif[274] == 1
        assert output.info['icc_profile']


def test_strip_keeps_color_profile_separate(tagged_source, tmp_path):
    result = export(tagged_source, tmp_path, 'strip')
    with Image.open(result.files[0].outputs[0]) as output:
        assert not output.getexif()
        assert output.info['icc_profile']


def test_sharing_removes_location_and_identifiers(tagged_source, tmp_path):
    result = export(tagged_source, tmp_path, 'sharing')
    with Image.open(result.files[0].outputs[0]) as output:
        exif = output.getexif()
        assert 34853 not in exif
        assert 271 not in exif
        assert 272 not in exif
        assert 315 not in exif
        assert 42033 not in exif.get_ifd(34665)
        assert exif.get_ifd(34665)[36867] == '2020:01:02 03:04:05'
        assert output.info['icc_profile']


def test_selected_tags_keep_only_named_metadata(tagged_source, tmp_path):
    result = export(
        tagged_source, tmp_path, 'selected', tags='DateTimeOriginal'
    )
    with Image.open(result.files[0].outputs[0]) as output:
        exif = output.getexif()
        assert 271 not in exif
        assert 34853 not in exif
        assert exif.get_ifd(34665)[36867] == '2020:01:02 03:04:05'
        assert 42033 not in exif.get_ifd(34665)


@pytest.mark.parametrize('orientation', range(1, 9))
@pytest.mark.parametrize('source_format', ['png', 'jpeg', 'tiff', 'webp'])
def test_orientation_is_normalized(
    tagged_source, tmp_path, orientation, source_format
):
    with Image.open(tagged_source) as source:
        image = source.crop((0, 0, 100, 70))
        exif = source.getexif()
        exif[274] = orientation
        oriented_source = tmp_path / ('oriented.' + source_format)
        image.save(oriented_source, exif=exif)
        image.close()
    with Image.open(oriented_source) as source:
        expected = ImageOps.exif_transpose(source).copy()
    result = export(oriented_source, tmp_path)
    assert result.status == 'success'
    with Image.open(result.files[0].outputs[0]) as output:
        assert output.getexif().get(274, 1) == 1
        assert output.size == expected.size
        assert output.tobytes() == expected.tobytes()
    expected.close()


def test_srgb_conversion_retains_alpha(tagged_source, tmp_path):
    with Image.open(tagged_source) as source:
        image = source.convert('RGBA')
        image.putalpha(128)
        image.save(
            tagged_source,
            exif=source.getexif(),
            icc_profile=source.info['icc_profile'],
        )
    result = export(tagged_source, tmp_path, color='srgb')
    assert result.status == 'success'
    with Image.open(result.files[0].outputs[0]) as output:
        assert output.mode == 'RGBA'
        assert output.getchannel('A').getextrema() == (128, 128)
        assert output.info['icc_profile']


def test_invalid_tag_selection_is_reported(tagged_source, tmp_path):
    result = export(tagged_source, tmp_path, 'selected', tags='UnknownTag')
    assert result.status == 'failed'
    assert not (tmp_path / 'output/tagged.png').exists()


def test_sharing_removes_xmp_and_png_text(tagged_source, tmp_path):
    with Image.open(tagged_source) as image:
        text = PngImagePlugin.PngInfo()
        text.add_text('Author', 'Test artist')
        text.add_itxt('XML:com.adobe.xmp', '<test>private</test>')
        image.save(
            tagged_source,
            pnginfo=text,
            exif=image.getexif(),
            icc_profile=image.info['icc_profile'],
        )
    result = export(tagged_source, tmp_path, 'sharing')
    with Image.open(result.files[0].outputs[0]) as output:
        assert 'Author' not in output.info
        assert 'XML:com.adobe.xmp' not in output.info
        assert output.info['icc_profile']


def test_preserve_reports_unsupported_metadata(tagged_source):
    with Image.open(tagged_source) as source:
        output, options, warnings = prepare_export(
            source, capture_metadata(source), 'BMP'
        )
    try:
        assert 'exif' not in options
        assert 'icc_profile' not in options
        assert any('EXIF' in warning for warning in warnings)
        assert any('ICC' in warning for warning in warnings)
    finally:
        output.close()


def test_invalid_profile_does_not_replace_existing_output(
    tagged_source, tmp_path
):
    with Image.open(tagged_source) as source:
        source.save(tagged_source, icc_profile=b'invalid test profile')
    target = tmp_path / 'output/tagged.png'
    target.parent.mkdir()
    target.write_bytes(b'previous output')
    result = export(tagged_source, tmp_path, color='srgb')
    assert result.status == 'failed'
    assert target.read_bytes() == b'previous output'
    assert not list(target.parent.glob('.*.tmp*'))


def test_palette_transparency_survives_srgb_conversion(test_input_dir):
    with Image.open(test_input_dir / 'frog.gif') as source:
        source.info['transparency'] = 0
        expected = source.convert('RGBA')
        output, options, warnings = prepare_export(
            source, capture_metadata(source), 'PNG', color_policy='srgb'
        )
    try:
        assert (
            output.getchannel('A').tobytes()
            == expected.getchannel('A').tobytes()
        )
        assert options['icc_profile']
        assert warnings
    finally:
        output.close()
        expected.close()


def test_native_srgb_conversion_changes_lab_pixels(test_input_dir):
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB'))
    lab = ImageCms.ImageCmsProfile(ImageCms.createProfile('LAB'))
    with Image.open(test_input_dir / 'frog.gif') as source:
        original = source.convert('RGB')
    tagged = ImageCms.profileToProfile(original, srgb, lab, outputMode='LAB')
    tagged.info['icc_profile'] = lab.tobytes()
    expected = ImageCms.profileToProfile(
        tagged,
        ImageCms.ImageCmsProfile(BytesIO(lab.tobytes())),
        srgb,
        outputMode='RGB',
    )
    output, options, warnings = prepare_export(
        tagged, capture_metadata(tagged), 'PNG', color_policy='srgb'
    )
    try:
        assert output.mode == 'RGB'
        assert output.tobytes() == expected.tobytes()
        assert not warnings
        assert options['icc_profile']
    finally:
        for image in (original, tagged, expected, output):
            image.close()


def test_preservation_rejects_profile_pixel_mismatch(tmp_path, test_input_dir):
    with Image.open(test_input_dir / 'frog.gif') as source:
        image = source.convert('RGB')
    # Simulate a transform that changed color space without updating its profile.
    path = tmp_path / 'mismatched.png'
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('LAB')).tobytes()
    image.save(path, icc_profile=profile)
    image.close()
    result = export(path, tmp_path)
    assert result.status == 'failed'
    assert 'ICC profile' in result.files[0].failures[0].message
    assert not (tmp_path / 'output/mismatched.png').exists()

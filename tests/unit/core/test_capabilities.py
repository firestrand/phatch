# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Modern exports exercise native codec availability and actual round trips."""

import pytest
from PIL import Image, ImageChops, ImageStat

from phatch.core import api, capabilities
from phatch.core.batch import plan_batch, run_batch


def save_action(tmp_path, format):
    api.import_actions()
    action = api.ACTIONS['Save']()
    action.set_field_as_string('In', str(tmp_path / 'outputs'))
    action.set_field_as_string('As', format)
    return action


@pytest.fixture
def transparent_source(tmp_path, test_input_dir):
    with Image.open(test_input_dir / 'frog.gif') as source:
        image = source.convert('RGBA')
    image.putalpha(128)
    # Invisible RGB values must also survive explicitly lossless export.
    image.putpixel((0, 0), (123, 45, 67, 0))
    path = tmp_path / 'transparent.png'
    image.save(path)
    image.close()
    return path


def test_lossless_webp_has_exact_pixels(transparent_source, tmp_path):
    if not capabilities.encoder_available('WEBP'):
        pytest.skip('WebP encoder unavailable')
    action = save_action(tmp_path, 'webp')
    action.set_field_as_string('WebP Lossless', 'yes')
    action.set_field_as_string('WebP Effort', '6')
    result = run_batch([action], [transparent_source])
    assert result.status == 'success'
    with (
        Image.open(transparent_source) as source,
        Image.open(result.files[0].outputs[0]) as output,
    ):
        assert output.format == 'WEBP'
        assert output.size == source.size
        assert output.convert('RGBA').tobytes() == source.tobytes()


@pytest.mark.parametrize('format', ['WEBP', 'AVIF'])
def test_lossy_export_has_bounded_color_error(
    transparent_source, tmp_path, format
):
    if not capabilities.encoder_available(format):
        pytest.skip(f'{format} encoder unavailable')
    action = save_action(tmp_path, format.lower())
    action.set_field_as_string(
        f'{"WebP" if format == "WEBP" else "AVIF"} Quality', '95'
    )
    result = run_batch([action], [transparent_source])
    assert result.status == 'success'
    with (
        Image.open(transparent_source) as source,
        Image.open(result.files[0].outputs[0]) as output,
    ):
        assert output.format == format
        assert output.size == source.size
        # A fixture-specific mean absolute channel error, in 8-bit levels.
        # Codec output is lossy, so exact color equality is inappropriate.
        difference = ImageChops.difference(
            source.convert('RGB'), output.convert('RGB')
        )
        assert max(ImageStat.Stat(difference).mean) < 12
        alpha_difference = ImageChops.difference(
            source.getchannel('A'), output.getchannel('A')
        )
        # AVIF compresses alpha at the chosen quality; WebP keeps it lossless.
        assert alpha_difference.getextrema()[1] <= (
            2 if format == 'AVIF' else 0
        )


def test_registered_but_missing_native_codec_fails_preflight(
    tmp_path, test_input_dir, monkeypatch
):
    original = capabilities.features.check
    monkeypatch.setattr(
        capabilities.features,
        'check',
        lambda name: False if name == 'webp' else original(name),
    )
    action = save_action(tmp_path, 'webp')
    plan = plan_batch([action], [test_input_dir / 'frog.gif'])
    assert not plan.valid
    issue = next(
        issue for issue in plan.issues if issue.code == 'unsupported_codec'
    )
    assert 'Install Pillow' in issue.message
    assert not (tmp_path / 'outputs').exists()


def test_explicit_png_fallback_plans_and_writes_correct_path(
    tmp_path, test_input_dir, monkeypatch
):
    original = capabilities.encoder_available
    monkeypatch.setattr(
        capabilities,
        'encoder_available',
        lambda name: False if name == 'WEBP' else original(name),
    )
    action = save_action(tmp_path, 'webp')
    action.set_field_as_string('Format Fallback', 'png')
    source = test_input_dir / 'frog.gif'
    plan = plan_batch([action], [source])
    assert plan.valid
    assert plan.files[0].destinations[0].path.suffix == '.png'
    result = run_batch([action], [source])
    assert result.status == 'success'
    assert result.files[0].outputs == [plan.files[0].destinations[0].path]
    assert not (tmp_path / 'outputs/frog.webp').exists()
    with Image.open(result.files[0].outputs[0]) as output:
        assert output.format == 'PNG'


@pytest.mark.parametrize(
    'options',
    [
        {'quality': -1},
        {'quality': 101},
        {'quality': True},
        {'effort': 7},
        {'lossless': 'yes'},
    ],
)
def test_webp_rejects_invalid_options(options):
    with pytest.raises(ValueError):
        capabilities.encoder_options('WEBP', **options)


@pytest.mark.parametrize(
    'options',
    [
        {'speed': -1},
        {'speed': 11},
        {'max_threads': 0},
        {'max_threads': 65},
    ],
)
def test_avif_rejects_invalid_options(options):
    with pytest.raises(ValueError):
        capabilities.encoder_options('AVIF', **options)


def test_capability_report_does_not_launch_external_tools(monkeypatch):
    names = []

    def locate(name):
        names.append(name)
        return '/test/tool' if name == 'tiffcp' else None

    monkeypatch.setattr(capabilities.shutil, 'which', locate)
    report = capabilities.capability_report()
    assert report['pillow_version']
    assert report['encoders']['PNG']
    assert report['external_tools']['tiffcp'] is True
    assert set(names) == set(report['external_tools'])
    assert '/test/tool' not in str(report)

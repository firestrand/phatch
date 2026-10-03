# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Configured previews render real pixels and never execute output actions."""

import pytest
from PIL import Image, ImageEnhance, ImageOps

from phatch.core import api
from phatch.core.workflow_preview import PreviewOptions, PreviewRenderer


@pytest.fixture
def workflow(tmp_path):
    api.import_actions()
    brightness = api.ACTIONS['Brightness']()
    brightness.set_field_as_string('Amount', '-50')
    save = api.ACTIONS['Save']()
    save.set_field_as_string('In', str(tmp_path / 'outputs'))
    save.set_field_as_string('As', 'png')
    return [brightness, api.ACTIONS['Invert'](), save]


def test_configured_sequence_matches_reference_pixels(
    workflow, test_input_dir, tmp_path
):
    source = test_input_dir / 'frog.gif'
    result = PreviewRenderer().render(source, workflow)
    assert result.status == 'success', result.failure
    assert result.skipped == ('Save',)
    assert len(result.steps) == 2
    with Image.open(source) as original:
        expected_before = original.convert('RGB')
        expected_after = ImageOps.invert(
            ImageEnhance.Brightness(expected_before).enhance(0.5)
        )
    with result.before.open() as before, result.after.open() as after:
        assert before.convert('RGB').tobytes() == expected_before.tobytes()
        assert after.convert('RGB').tobytes() == expected_after.tobytes()
    assert not (tmp_path / 'outputs').exists()


def test_preview_parameters_invalidate_cached_result(workflow, test_input_dir):
    renderer = PreviewRenderer()
    source = test_input_dir / 'frog.gif'
    initial = renderer.render(source, workflow)
    repeated = renderer.render(source, workflow)
    assert repeated.cache_hit
    assert repeated.cache_key == initial.cache_key
    workflow[0].set_field_as_string('Amount', '50')
    changed = renderer.render(source, workflow)
    assert not changed.cache_hit
    assert changed.cache_key != initial.cache_key
    assert changed.after.png != initial.after.png
    scaled = renderer.render(source, workflow, PreviewOptions(size=(64, 64)))
    assert scaled.cache_key != changed.cache_key
    assert scaled.before.size == (64, 64)
    assert scaled.approximate


def test_full_resolution_crop_is_applied_after_workflow(
    workflow, test_input_dir
):
    result = PreviewRenderer().render(
        test_input_dir / 'frog.gif',
        workflow,
        PreviewOptions(crop=(20, 30, 60, 70)),
    )
    assert result.status == 'success'
    assert not result.approximate
    assert result.after.size == (40, 40)
    with Image.open(test_input_dir / 'frog.gif') as source:
        expected = ImageOps.invert(
            ImageEnhance.Brightness(source.convert('RGB')).enhance(0.5)
        )
        expected = expected.crop((20, 30, 60, 70))
    with result.after.open() as output:
        assert output.convert('RGB').tobytes() == expected.tobytes()


def test_preview_cancellation_does_not_write_or_cache(
    workflow, test_input_dir, tmp_path
):
    renderer = PreviewRenderer()
    cancelled = False

    def progress(index, label):
        nonlocal cancelled
        cancelled = True

    result = renderer.render(
        test_input_dir / 'frog.gif',
        workflow,
        progress=progress,
        cancel=lambda: cancelled,
    )
    assert result.status == 'cancelled'
    assert not (tmp_path / 'outputs').exists()
    retry = renderer.render(test_input_dir / 'frog.gif', workflow)
    assert retry.status == 'success'
    assert not retry.cache_hit


@pytest.mark.parametrize('declaration', [None, False, 'true', 1, []])
def test_unsupported_custom_action_is_never_initialized_or_run(
    workflow, test_input_dir, declaration
):
    class SideEffect:
        label = 'Side effect'

        def is_enabled(self):
            return True

        def init(self):
            raise AssertionError('initialized unsupported action')

        def apply(self, *args):
            raise AssertionError('executed unsupported action')

    SideEffect.preview_safe = declaration
    result = PreviewRenderer().render(
        test_input_dir / 'frog.gif', [SideEffect(), *workflow]
    )
    assert result.status == 'success'
    assert result.skipped == ('Side effect', 'Save')


def test_cache_does_not_expose_live_mutable_images(workflow, test_input_dir):
    renderer = PreviewRenderer()
    source = test_input_dir / 'frog.gif'
    first = renderer.render(source, workflow)
    with first.after.open() as mutable:
        mutable.paste((0, 0, 0), (0, 0, *mutable.size))
    again = renderer.render(source, workflow)
    assert again.cache_hit
    assert again.after.png == first.after.png


def test_resource_and_result_limits_are_visible(workflow, test_input_dir):
    source = test_input_dir / 'frog.gif'
    result = PreviewRenderer().render(
        source, workflow, PreviewOptions(max_source_pixels=100)
    )
    assert result.status == 'failed'
    assert 'pixel limit' in result.failure.message
    result = PreviewRenderer().render(
        source, workflow, PreviewOptions(max_result_bytes=100)
    )
    assert result.status == 'failed'
    assert 'byte limit' in result.failure.message


def test_cache_eviction_respects_byte_budget(workflow, test_input_dir):
    source = test_input_dir / 'frog.gif'
    sample = PreviewRenderer(cache_bytes=0).render(source, workflow)
    renderer = PreviewRenderer(cache_bytes=sample.byte_size)
    assert renderer.render(source, workflow).status == 'success'
    workflow[0].set_field_as_string('Amount', '50')
    assert renderer.render(source, workflow).status == 'success'
    workflow[0].set_field_as_string('Amount', '-50')
    assert not renderer.render(source, workflow).cache_hit


def test_resource_changes_invalidate_watermark_preview(
    test_input_dir, tmp_path
):
    api.import_actions()
    mark = tmp_path / 'mark.png'
    with Image.open(test_input_dir / 'frog.gif') as source:
        source.convert('RGBA').crop((0, 0, 30, 30)).save(mark)
    watermark = api.ACTIONS['Watermark']()
    watermark.set_field_as_string('Mark', str(mark))
    renderer = PreviewRenderer()
    source = test_input_dir / 'frog.gif'
    initial = renderer.render(source, [watermark])
    assert initial.status == 'success', initial.failure
    assert renderer.render(source, [watermark]).cache_hit
    with Image.open(mark) as image:
        changed = image.copy()
    changed.paste((0, 0, 0, 255), (0, 0, *changed.size))
    changed.save(mark)
    changed.close()
    updated = renderer.render(source, [watermark])
    assert updated.status == 'success', updated.failure
    assert not updated.cache_hit
    assert updated.cache_key != initial.cache_key
    assert updated.after.png != initial.after.png


def test_preview_enforces_safe_parameters_when_editor_safe_mode_is_off(
    workflow, test_input_dir, tmp_path, monkeypatch
):
    from lib.formField import Field

    monkeypatch.setattr(Field, 'safe', False)
    target = tmp_path / 'must-not-exist'
    workflow[0].set_field_as_string(
        'Amount', f'<open({str(target)!r}, "w").write("test")>'
    )
    result = PreviewRenderer().render(test_input_dir / 'frog.gif', workflow)
    assert result.status == 'failed'
    assert not target.exists()
    assert Field.safe is False


def test_preview_does_not_write_font_cache(
    test_input_dir, tmp_path, monkeypatch
):
    api.import_actions()
    from lib import fonts

    monkeypatch.setattr(fonts, '_FONT_DICTIONARY', None)
    monkeypatch.setattr(
        fonts, 'ROOT_FONTS_CACHE_PATH', str(tmp_path / 'missing-root-cache')
    )
    monkeypatch.setattr(
        fonts, 'USER_FONTS_CACHE_PATH', str(tmp_path / 'missing-user-cache')
    )
    target = tmp_path / 'font-cache'
    monkeypatch.setattr(fonts, 'WRITABLE_FONTS_CACHE_PATH', str(target))
    text = api.ACTIONS['Text']()
    text.set_field_as_string(
        'Font', str(test_input_dir.parents[1] / 'data/fonts/FreeSans.ttf')
    )
    result = PreviewRenderer().render(test_input_dir / 'frog.gif', [text])
    assert result.status == 'success', result.failure
    assert not target.exists()


def test_source_content_change_invalidates_preview(
    workflow, test_input_dir, tmp_path
):
    path = tmp_path / 'changing.png'
    with Image.open(test_input_dir / 'frog.gif') as image:
        image.convert('RGB').save(path)
    renderer = PreviewRenderer()
    initial = renderer.render(path, workflow)
    assert renderer.render(path, workflow).cache_hit
    with Image.open(path) as image:
        cropped = image.crop((0, 0, 80, 60))
    cropped.save(path)
    cropped.close()
    changed = renderer.render(path, workflow)
    assert changed.status == 'success'
    assert not changed.cache_hit
    assert changed.cache_key != initial.cache_key
    assert changed.before.size == (80, 60)


def test_font_file_change_invalidates_preview(test_input_dir, tmp_path):
    api.import_actions()
    font = tmp_path / 'font.ttf'
    font.write_bytes(
        (test_input_dir.parents[1] / 'data/fonts/FreeSans.ttf').read_bytes()
    )
    text = api.ACTIONS['Text']()
    text.set_field_as_string('Font', str(font))
    renderer = PreviewRenderer()
    source = test_input_dir / 'frog.gif'
    initial = renderer.render(source, [text])
    assert initial.status == 'success', initial.failure
    assert renderer.render(source, [text]).cache_hit
    # Harmless trailing padding changes the resource identity without creating
    # a malformed font or modifying a repository-owned fixture.
    with font.open('ab') as stream:
        stream.write(b'\0')
    changed = renderer.render(source, [text])
    assert changed.status == 'success', changed.failure
    assert not changed.cache_hit
    assert changed.cache_key != initial.cache_key


def test_importable_plugin_declared_resource_previews_without_outputs(
    test_input_dir, tmp_path
):
    from tests.fixtures.resource_action import Action
    from io import BytesIO

    color = tmp_path / 'color-0-0.txt'
    color.write_text('blue')
    action = Action()
    action.set_field_as_string(
        'Color File', str(tmp_path / 'color-<repeatindex>-<frameindex>.txt')
    )
    result = PreviewRenderer().render(test_input_dir / 'frog.gif', [action])
    assert result.status == 'success', result.failure
    with Image.open(BytesIO(result.after.png)) as image:
        assert image.getpixel((0, 0))[:3] == (0, 0, 255)
    assert list(tmp_path.iterdir()) == [color]


def test_original_parameter_edits_do_not_mutate_running_snapshot(
    workflow, test_input_dir
):
    renderer = PreviewRenderer()
    initial = renderer.render(test_input_dir / 'frog.gif', workflow)

    def change(index, label):
        workflow[0].set_field_as_string('Amount', '50')

    snapshot = renderer.render(
        test_input_dir / 'frog.gif',
        workflow,
        PreviewOptions(full_resolution=True),
        progress=change,
    )
    assert snapshot.status == 'success'
    assert snapshot.after.png == initial.after.png
    assert workflow[0].get_field_string('Amount') == '50'

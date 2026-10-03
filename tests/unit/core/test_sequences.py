# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sequence policies preserve decoded playback, page content and timing."""

import pytest
import struct
from types import SimpleNamespace
from PIL import Image, ImageCms, ImageOps

from phatch.core import api
from phatch.core.batch import plan_batch, run_batch


@pytest.fixture
def animation(tmp_path):
    source = tmp_path / 'moving.gif'
    frames = [
        Image.new('RGB', (16, 10), color) for color in ('red', 'blue', 'green')
    ]
    try:
        frames[0].save(
            source,
            save_all=True,
            append_images=frames[1:],
            duration=[40, 80, 120],
            loop=3,
            disposal=2,
        )
    finally:
        for frame in frames:
            frame.close()
    return source


def workflow(tmp_path, format='png', invert=False):
    api.import_actions()
    save = api.ACTIONS['Save']()
    save.set_field_as_string('In', str(tmp_path / 'outputs'))
    save.set_field_as_string('As', format)
    save.set_field_as_string('WebP Lossless', 'yes')
    return [api.ACTIONS['Invert'](), save] if invert else [save]


def frames(path):
    result = []
    durations = []
    with Image.open(path) as image:
        loop = image.info.get('loop')
        for index in range(image.n_frames):
            image.seek(index)
            image.load()
            durations.append(round(image.info.get('duration', 0)))
            converted = image.convert('RGB')
            result.append((converted.size, converted.tobytes()))
            converted.close()
    return result, durations, loop


@pytest.fixture
def tagged_pages(tmp_path, request):
    source = tmp_path / 'tagged-pages.tiff'
    profile = ImageCms.ImageCmsProfile(
        ImageCms.createProfile('sRGB')
    ).tobytes()
    pages = []
    expected = []
    for index, orientation in enumerate(range(1, 9)):
        page = Image.new('RGB', (6 + index, 4))
        page.putdata(
            [
                ((x * 31) % 256, y * 47, index * 29)
                for y in range(4)
                for x in range(page.width)
            ]
        )
        metadata = Image.Exif()
        metadata[274] = orientation
        metadata[270] = f'Page {index}'
        metadata[315] = f'Synthetic author {index}'
        # Pillow's TIFF appender does not relocate nested GPS offsets on later
        # pages. Keep the GPS-bearing first page valid, with distinct later tags.
        if index == 0 or getattr(request, 'param', None) == 'later-gps':
            metadata[34853] = {1: 'N', 2: (1.0, 2.0, 3.0)}
        metadata[700] = f'<private>Page {index}</private>'.encode()
        page.info['exif'] = metadata.tobytes()
        page.encoderinfo = {
            'exif': metadata.tobytes(),
            'icc_profile': profile if index % 2 == 0 else None,
        }
        with ImageOps.exif_transpose(page) as normalized:
            expected.append((normalized.size, normalized.tobytes()))
        pages.append(page)
    try:
        pages[0].save(source, save_all=True, append_images=pages[1:])
    finally:
        for page in pages:
            page.close()
    if getattr(request, 'param', None) == 'later-gps':
        # Make a valid classic TIFF whose page IFDs share the first GPS IFD.
        # This repairs Pillow's page-relative GPS offsets in the generated
        # fixture; production must reject an unrepresentable preservation.
        data = bytearray(source.read_bytes())
        assert data[:4] == b'II*\x00'
        offset = struct.unpack_from('<I', data, 4)[0]
        gps_offset = None
        while offset:
            count = struct.unpack_from('<H', data, offset)[0]
            for entry in range(count):
                position = offset + 2 + entry * 12
                tag, kind, length, value = struct.unpack_from(
                    '<HHII', data, position
                )
                if tag == 34853:
                    assert kind == 4 and length == 1
                    if gps_offset is None:
                        gps_offset = value
                    struct.pack_into('<I', data, position + 8, gps_offset)
            offset = struct.unpack_from('<I', data, offset + 2 + count * 12)[0]
        source.write_bytes(data)
    return source, expected, profile


@pytest.mark.parametrize(
    'policy', ['preserve', 'strip', 'selected', 'sharing']
)
@pytest.mark.parametrize('sequence_policy', ['preserve', 'extract'])
def test_tiff_pages_keep_independent_metadata_and_oriented_pixels(
    tmp_path, tagged_pages, policy, sequence_policy
):
    source, expected, profile = tagged_pages
    actions = workflow(tmp_path, 'tiff')
    actions[-1].set_field_as_string('Metadata Policy', policy)
    actions[-1].set_field_as_string('Metadata Tags', 'ImageDescription')
    settings = {'page_policy': sequence_policy}
    plan = plan_batch(actions, [source], settings)
    assert plan.valid, plan.issues
    from phatch.core.sequences import inspect_sequence

    assert inspect_sequence(source, settings).sizes == tuple(
        size for size, _ in expected
    )
    result = run_batch(actions, [source], settings)
    assert result.status == 'success', result.to_dict(include_details=True)
    observed = []
    index = 0
    for path in result.files[0].outputs:
        with Image.open(path) as output:
            for page_index in range(output.n_frames):
                output.seek(page_index)
                output.load()
                observed.append((output.size, output.tobytes()))
                tags = output.getexif()
                assert tags.get(274, 1) == 1
                assert (tags[256], tags[257]) == output.size
                assert tags.get(270) == (
                    f'Page {index}'
                    if policy in {'preserve', 'selected'}
                    else None
                )
                assert tags.get(315) == (
                    f'Synthetic author {index}'
                    if policy == 'preserve'
                    else None
                )
                assert (34853 in tags) == (policy == 'preserve' and index == 0)
                if 34853 in tags:
                    assert tuple(tags.get_ifd(34853)[2]) == (1.0, 2.0, 3.0)
                assert tags.get(700) == (
                    f'<private>Page {index}</private>'.encode()
                    if policy == 'preserve'
                    else None
                )
                # Read the page's own IFD: Pillow's info can retain prior ICC data.
                assert output.tag_v2.get(34675) == (
                    profile if index % 2 == 0 else None
                )
                index += 1
    assert observed == expected


@pytest.mark.parametrize('compression', ['lzw', 'zip', 'packbits'])
def test_compressed_pages_keep_safe_metadata_and_profile(
    tmp_path, tagged_pages, compression
):
    source, expected, profile = tagged_pages
    actions = workflow(tmp_path, 'tiff')
    actions[-1].set_field_as_string('Metadata Policy', 'selected')
    actions[-1].set_field_as_string('Metadata Tags', 'ImageDescription')
    actions[-1].set_field_as_string('TIFF Compression', compression)
    result = run_batch(actions, [source], {'page_policy': 'preserve'})
    assert result.status == 'success', result.to_dict(include_details=True)
    assert frames(result.files[0].outputs[0])[0] == expected
    with Image.open(result.files[0].outputs[0]) as output:
        for index in range(output.n_frames):
            output.seek(index)
            output.load()
            assert (
                output.tag_v2[259]
                == {'lzw': 5, 'zip': 8, 'packbits': 32773}[compression]
            )
            assert output.getexif()[270] == f'Page {index}'
            assert output.tag_v2.get(34675) == (
                profile if index % 2 == 0 else None
            )


def test_compressed_page_subifds_fail_explicitly_without_replacing_target(
    tmp_path, tagged_pages
):
    source, _, _ = tagged_pages
    target = tmp_path / 'outputs' / source.name
    target.parent.mkdir()
    target.write_bytes(b'Existing target')
    actions = workflow(tmp_path, 'tiff')
    actions[-1].set_field_as_string('TIFF Compression', 'lzw')
    result = run_batch(actions, [source], {'page_policy': 'preserve'})
    assert result.status == 'failed'
    assert 'EXIF/GPS sub-IFDs' in result.files[0].failures[0].message
    assert target.read_bytes() == b'Existing target'
    assert not list(target.parent.glob('.*'))


@pytest.mark.parametrize('tagged_pages', ['later-gps'], indirect=True)
def test_appended_page_subifds_reject_preservation_and_extract_safely(
    tmp_path, tagged_pages
):
    source, expected, _ = tagged_pages
    # Establish that the synthetic input's nested directories are readable.
    with Image.open(source) as image:
        for index in range(image.n_frames):
            image.seek(index)
            assert tuple(image.getexif().get_ifd(34853)[2]) == (1.0, 2.0, 3.0)
    actions = workflow(tmp_path, 'tiff')
    target = tmp_path / 'outputs' / source.name
    target.parent.mkdir()
    target.write_bytes(b'Existing target')
    rejected = run_batch(actions, [source], {'page_policy': 'preserve'})
    assert rejected.status == 'failed'
    assert 'page extraction' in rejected.files[0].failures[0].message
    assert target.read_bytes() == b'Existing target'
    assert not list(target.parent.glob('.*'))
    extracted = run_batch(actions, [source], {'page_policy': 'extract'})
    assert extracted.status == 'success', extracted.to_dict(
        include_details=True
    )
    for path, pixels in zip(extracted.files[0].outputs, expected):
        with Image.open(path) as output:
            output.load()
            assert (output.size, output.tobytes()) == pixels
            assert tuple(output.getexif().get_ifd(34853)[2]) == (1.0, 2.0, 3.0)


@pytest.mark.parametrize('color', ['preserve', 'srgb'])
def test_animation_differing_profiles_require_srgb(tmp_path, color):
    from phatch.core.export_policy import SourceMetadata
    from phatch.core.sequences import (
        SequenceError,
        SequenceInfo,
        save_sequence,
    )

    target = tmp_path / 'animation.webp'
    target.write_bytes(b'Existing target')
    profile = ImageCms.ImageCmsProfile(
        ImageCms.createProfile('sRGB')
    ).tobytes()
    first = Image.new('RGB', (8, 4), 'red')
    second = Image.new('RGB', (8, 4), 'blue')
    log = []
    photo = SimpleNamespace(
        sequence_info=SequenceInfo('WEBP', 2, 'animation', (40, 80), 2),
        sequence_members=[
            SimpleNamespace(
                get_flattened_image=first.copy,
                source_metadata=SourceMetadata(icc_profile=profile),
            ),
            SimpleNamespace(
                get_flattened_image=second.copy,
                source_metadata=SourceMetadata(),
            ),
        ],
        log=log.append,
        append_to_report=lambda *args: None,
    )
    try:
        if color == 'preserve':
            with pytest.raises(SequenceError, match='one ICC profile'):
                save_sequence(
                    photo,
                    str(target),
                    'WEBP',
                    True,
                    'replace',
                    {'lossless': True},
                )
            assert target.read_bytes() == b'Existing target'
            assert not list(tmp_path.glob('.*'))
        else:
            save_sequence(
                photo,
                str(target),
                'WEBP',
                True,
                'replace',
                {'lossless': True, 'color_policy': color},
            )
            with Image.open(target) as output:
                assert output.n_frames == 2
                assert output.info['icc_profile']
                output.seek(0)
                with output.convert('RGB') as pixels:
                    assert pixels.getpixel((0, 0)) == (255, 0, 0)
                output.seek(1)
                with output.convert('RGB') as pixels:
                    assert pixels.getpixel((0, 0)) == (0, 0, 255)
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize('format', ['png', 'tiff', 'webp', 'avif'])
@pytest.mark.parametrize(
    'policy', ['preserve', 'strip', 'selected', 'sharing']
)
def test_first_tiff_page_payloads_follow_export_policy(
    tmp_path, tagged_pages, format, policy
):
    source, _, profile = tagged_pages
    actions = workflow(tmp_path, format)
    actions[-1].set_field_as_string('Metadata Policy', policy)
    actions[-1].set_field_as_string('Metadata Tags', 'ImageDescription')
    result = run_batch(actions, [source], {'page_policy': 'first'})
    assert result.status == 'success', result.to_dict(include_details=True)
    with Image.open(result.files[0].outputs[0]) as output:
        output.load()
        tags = output.getexif()
        assert tags.get(270) == (
            'Page 0' if policy in {'preserve', 'selected'} else None
        )
        assert (34853 in tags) == (policy == 'preserve')
        assert output.info['icc_profile'] == profile
        xmp = output.info.get('xmp') or output.info.get('XML:com.adobe.xmp')
        if isinstance(xmp, str):
            xmp = xmp.encode()
        assert xmp == (
            b'<private>Page 0</private>' if policy == 'preserve' else None
        )


def test_tagged_pages_use_spawned_workers_and_verified_resume(
    tmp_path, tagged_pages
):
    source, expected, profile = tagged_pages
    second = tmp_path / 'second.tiff'
    second.write_bytes(source.read_bytes())
    actions = workflow(tmp_path, 'tiff')
    settings = {
        'workers': 2,
        'page_policy': 'preserve',
        'manifest_path': tmp_path / 'journal.json',
    }
    first = run_batch(actions, [source, second], settings)
    assert first.status == 'success', first.to_dict(include_details=True)
    assert first.execution['effective_workers'] == 2
    for result in first.files:
        assert frames(result.outputs[0])[0] == expected
        with Image.open(result.outputs[0]) as output:
            for index in range(output.n_frames):
                output.seek(index)
                assert output.getexif()[270] == f'Page {index}'
                assert output.tag_v2.get(34675) == (
                    profile if index % 2 == 0 else None
                )
    resumed = run_batch(
        actions, [source, second], {**settings, 'resume': True}
    )
    assert resumed.status == 'success'
    assert all(item.resumed for item in resumed.files)


def test_animation_reports_container_metadata_choice(tmp_path):
    from phatch.core.export_policy import SourceMetadata
    from phatch.core.sequences import SequenceInfo, save_sequence

    images = [Image.new('RGB', (8, 4), color) for color in ('red', 'blue')]
    members = []
    for index, image in enumerate(images):
        exif = Image.Exif()
        exif[270] = f'Frame {index}'
        members.append(
            SimpleNamespace(
                get_flattened_image=image.copy,
                source_metadata=SourceMetadata(exif=exif.tobytes()),
            )
        )
    warnings = []
    photo = SimpleNamespace(
        sequence_info=SequenceInfo('WEBP', 2, 'animation', (40, 80), 2),
        sequence_members=members,
        log=warnings.append,
        append_to_report=lambda *args: None,
    )
    target = tmp_path / 'animation.webp'
    try:
        save_sequence(
            photo, str(target), 'WEBP', True, 'replace', {'lossless': True}
        )
        with Image.open(target) as output:
            assert output.getexif()[270] == 'Frame 0'
            assert output.n_frames == 2
        assert any(
            'frame 1 metadata differs' in warning for warning in warnings
        )
    finally:
        for image in images:
            image.close()


def test_default_reject_is_side_effect_free(tmp_path, animation):
    actions = workflow(tmp_path)
    plan = plan_batch(actions, [animation])
    assert not plan.valid
    assert any(issue.code == 'invalid_sequence' for issue in plan.issues)
    result = run_batch(actions, [animation])
    assert result.status == 'invalid_setup'
    assert not (tmp_path / 'outputs').exists()


def test_explicit_first_reports_discarded_frames(tmp_path, animation):
    result = run_batch(
        workflow(tmp_path), [animation], {'animation_policy': 'first'}
    )
    assert result.status == 'success', result.to_dict(include_details=True)
    with Image.open(result.files[0].outputs[0]) as image:
        assert getattr(image, 'n_frames', 1) == 1
    assert any(
        'discarded 2' in message for message in result.files[0].warnings
    )


@pytest.mark.parametrize('format', ['gif', 'png', 'webp'])
def test_preserve_transformed_playback(tmp_path, animation, format):
    result = run_batch(
        workflow(tmp_path, format, invert=True),
        [animation],
        {'animation_policy': 'preserve'},
    )
    assert result.status == 'success', result.to_dict(include_details=True)
    output, durations, loop = frames(result.files[0].outputs[0])
    expected = []
    with Image.open(animation) as original:
        for index in range(original.n_frames):
            original.seek(index)
            rgb = original.convert('RGB')
            inverted = ImageOps.invert(rgb)
            expected.append((inverted.size, inverted.tobytes()))
            rgb.close()
            inverted.close()
    assert output == expected
    assert durations == [40, 80, 120]
    assert loop == 3


def test_extract_paths_match_preflight_and_frame_pixels(tmp_path, animation):
    actions = workflow(tmp_path)
    actions[-1].set_field_as_string('File Name', '<filename>-<frameindex>')
    settings = {'animation_policy': 'extract'}
    plan = plan_batch(actions, [animation], settings)
    assert plan.valid, plan.issues
    result = run_batch(actions, [animation], settings)
    assert result.status == 'success', result.to_dict(include_details=True)
    assert result.files[0].outputs == [
        destination.path for destination in plan.files[0].destinations
    ]
    expected, _, _ = frames(animation)
    for output, pixels in zip(result.files[0].outputs, expected):
        with Image.open(output) as image:
            rgb = image.convert('RGB')
            assert (rgb.size, rgb.tobytes()) == pixels
            rgb.close()


def test_pages_preserve_different_dimensions(tmp_path):
    source = tmp_path / 'pages.tiff'
    first = Image.new('RGB', (16, 10), 'red')
    second = Image.new('RGB', (8, 20), 'blue')
    first.save(source, save_all=True, append_images=[second])
    first.close()
    second.close()
    actions = workflow(tmp_path, 'tiff')
    assert not plan_batch(
        actions, [source], {'animation_policy': 'preserve'}
    ).valid
    result = run_batch(actions, [source], {'page_policy': 'preserve'})
    assert result.status == 'success', result.to_dict(include_details=True)
    assert frames(result.files[0].outputs[0])[0] == frames(source)[0]


def test_incompatible_preservation_encoder_rejected(tmp_path, animation):
    plan = plan_batch(
        workflow(tmp_path, 'jpeg'),
        [animation],
        {'animation_policy': 'preserve'},
    )
    assert not plan.valid
    assert not (tmp_path / 'outputs').exists()


def test_frame_limit_rejects_before_outputs(tmp_path, animation):
    result = run_batch(
        workflow(tmp_path),
        [animation],
        {'animation_policy': 'extract', 'max_sequence_frames': 2},
    )
    assert result.status == 'invalid_setup'
    assert not (tmp_path / 'outputs').exists()


def test_recipe_policy_controls_and_batch_override(tmp_path, animation):
    actions = workflow(tmp_path)
    actions[-1].set_field_as_string('Animation Policy', 'extract')
    assert plan_batch(actions, [animation]).valid
    assert not plan_batch(
        actions, [animation], {'animation_policy': 'reject'}
    ).valid
    result = run_batch(actions, [animation])
    assert result.status == 'success'
    assert len(result.files[0].outputs) == 3


@pytest.mark.parametrize('format', ['gif', 'png', 'webp'])
def test_composited_transparency_and_disposal(tmp_path, format):
    source = tmp_path / 'disposal.gif'
    palette = [0, 0, 0, 255, 0, 0, 0, 0, 255, 0, 255, 0] + [0] * (768 - 12)
    originals = []
    for index in range(3):
        frame = Image.new('P', (16, 10), 0)
        frame.putpalette(palette)
        for x in range(index * 4, index * 4 + 4):
            for y in range(3, 7):
                frame.putpixel((x, y), index + 1)
        originals.append(frame)
    try:
        originals[0].save(
            source,
            save_all=True,
            append_images=originals[1:],
            transparency=0,
            duration=[40, 80, 120],
            disposal=[1, 2, 3],
            loop=0,
            optimize=False,
        )
    finally:
        for frame in originals:
            frame.close()
    result = run_batch(
        workflow(tmp_path, format), [source], {'animation_policy': 'preserve'}
    )
    assert result.status == 'success', result.to_dict(include_details=True)
    with (
        Image.open(source) as expected,
        Image.open(result.files[0].outputs[0]) as actual,
    ):
        assert actual.n_frames == expected.n_frames
        for index in range(expected.n_frames):
            expected.seek(index)
            actual.seek(index)
            left = expected.convert('RGBA')
            right = actual.convert('RGBA')
            try:
                assert (
                    right.getchannel('A').tobytes()
                    == left.getchannel('A').tobytes()
                )
                background = Image.new('RGBA', left.size, 'white')
                composite_left = Image.alpha_composite(background, left)
                composite_right = Image.alpha_composite(background, right)
                assert composite_left.tobytes() == composite_right.tobytes()
                composite_left.close()
                composite_right.close()
                background.close()
            finally:
                left.close()
                right.close()


def test_extraction_cancel_reports_completed_frame(tmp_path, animation):
    first = tmp_path / 'outputs/moving-frame-0000.png'
    result = run_batch(
        workflow(tmp_path),
        [animation],
        {'animation_policy': 'extract'},
        cancel=first.exists,
    )
    assert result.status == 'cancelled'
    assert result.files[0].outputs == [first]
    assert not (tmp_path / 'outputs/moving-frame-0001.png').exists()


def test_sequence_resume_verifies_all_frames(tmp_path, animation):
    actions = workflow(tmp_path)
    settings = {
        'animation_policy': 'extract',
        'manifest_path': tmp_path / 'job.json',
    }
    initial = run_batch(actions, [animation], settings)
    assert initial.status == 'success'
    resumed = run_batch(actions, [animation], {**settings, 'resume': True})
    assert resumed.files[0].resumed
    assert len(resumed.files[0].outputs) == 3
    initial.files[0].outputs[-1].unlink()
    rerun = run_batch(actions, [animation], {**settings, 'resume': True})
    assert rerun.status == 'success'
    assert not rerun.files[0].resumed


def test_sequence_failure_preserves_previous_target(
    tmp_path, animation, monkeypatch
):
    previous = tmp_path / 'outputs/moving.png'
    previous.parent.mkdir()
    previous.write_bytes(b'previous output')
    original = Image.Image.save

    def fail_sequence(self, path, *args, **kwargs):
        if kwargs.get('save_all'):
            raise OSError('injected sequence encoder failure')
        return original(self, path, *args, **kwargs)

    monkeypatch.setattr(Image.Image, 'save', fail_sequence)
    result = run_batch(
        workflow(tmp_path), [animation], {'animation_policy': 'preserve'}
    )
    assert result.status == 'failed'
    assert previous.read_bytes() == b'previous output'
    assert list(previous.parent.iterdir()) == [previous]


def test_avif_sequence_preserves_frame_count_and_timing(tmp_path):
    from phatch.core.capabilities import encoder_available

    if not encoder_available('AVIF'):
        pytest.skip('AVIF encoder unavailable')
    source = tmp_path / 'moving.avif'
    originals = [
        Image.new('RGB', (16, 10), color) for color in ('red', 'blue', 'green')
    ]
    try:
        originals[0].save(
            source,
            save_all=True,
            append_images=originals[1:],
            duration=[40, 80, 120],
            quality=100,
            speed=10,
            max_threads=1,
        )
    finally:
        for image in originals:
            image.close()
    actions = workflow(tmp_path, 'avif')
    actions[-1].set_field_as_string('AVIF Quality', '100')
    result = run_batch(actions, [source], {'animation_policy': 'preserve'})
    assert result.status == 'success', result.to_dict(include_details=True)
    actual, durations, _ = frames(result.files[0].outputs[0])
    expected, expected_durations, _ = frames(source)
    assert len(actual) == len(expected) == 3
    assert durations == expected_durations == [40, 80, 120]
    for (_, left), (_, right) in zip(actual, expected):
        assert max(abs(a - b) for a, b in zip(left, right)) <= 4


def test_apng_poster_is_retained_only_in_supported_format(tmp_path):
    source = tmp_path / 'poster.png'
    poster = Image.new('RGBA', (16, 10), 'white')
    playback = [
        Image.new('RGBA', (16, 10), color) for color in ('red', 'blue')
    ]
    try:
        poster.save(
            source,
            save_all=True,
            append_images=playback,
            default_image=True,
            duration=[40, 80],
            loop=2,
        )
    finally:
        poster.close()
        for image in playback:
            image.close()
    settings = {'animation_policy': 'preserve'}
    assert not plan_batch(workflow(tmp_path, 'webp'), [source], settings).valid
    result = run_batch(workflow(tmp_path), [source], settings)
    assert result.status == 'success', result.to_dict(include_details=True)
    assert frames(result.files[0].outputs[0]) == frames(source)
    with Image.open(result.files[0].outputs[0]) as output:
        assert output.info['default_image']


def test_decoded_memory_limit_rejects_before_processing(tmp_path, animation):
    result = run_batch(
        workflow(tmp_path),
        [animation],
        {'animation_policy': 'extract', 'sequence_memory_bytes': 1000},
    )
    assert result.status == 'invalid_setup'
    assert not (tmp_path / 'outputs').exists()


def test_unsupported_action_rejected_without_initialization(
    tmp_path, animation
):
    class Unsafe:
        label = 'Side effect'

        def is_enabled(self):
            return True

        def dump(self):
            return {'fields': {}}

        def init(self):
            raise AssertionError('Unsupported action initialized')

        def apply(self, *args):
            raise AssertionError('Unsupported action executed')

    result = run_batch(
        [Unsafe(), *workflow(tmp_path)],
        [animation],
        {'animation_policy': 'preserve'},
    )
    assert result.status == 'invalid_setup'
    assert not (tmp_path / 'outputs').exists()


def test_extracted_variants_have_distinct_artifacts(tmp_path, animation):
    from phatch.core.variants import Variant, variant_action

    api.import_actions()
    actions = [
        variant_action([Variant('small', 8, 8, 'png')], tmp_path / 'outputs')
    ]
    settings = {'animation_policy': 'extract'}
    plan = plan_batch(actions, [animation], settings)
    assert plan.valid
    result = run_batch(actions, [animation], settings)
    assert result.status == 'success', result.to_dict(include_details=True)
    assert len(result.files[0].outputs) == 3
    assert len(result.files[0].artifacts) == 3
    assert set(result.files[0].outputs + result.files[0].artifacts) == {
        dest.path for dest in plan.files[0].destinations
    }


@pytest.mark.parametrize('corruption', ['count', 'duration', 'loop', 'dimensions'])
def test_sequence_validation_preserves_target_after_encoder_corruption(
    tmp_path, animation, monkeypatch, corruption
):
    previous = tmp_path / 'outputs/moving.gif'
    previous.parent.mkdir()
    previous.write_bytes(b'original')
    original_save = Image.Image.save

    def corrupt(image, target, *args, **options):
        if not options.get('save_all'):
            return original_save(image, target, *args, **options)
        if corruption == 'count':
            options['append_images'] = []
        elif corruption == 'duration':
            options['duration'] = [10, 10, 10]
        elif corruption == 'loop':
            options['loop'] = 0
        else:
            smaller = [frame.resize((8, 5)) for frame in [image, *options['append_images']]]
            try:
                options['append_images'] = smaller[1:]
                return original_save(smaller[0], target, *args, **options)
            finally:
                for frame in smaller:
                    frame.close()
        return original_save(image, target, *args, **options)

    monkeypatch.setattr(Image.Image, 'save', corrupt)
    result = run_batch(
        workflow(tmp_path, 'gif'), [animation],
        {'animation_policy': 'preserve', 'collision_policy': 'replace'},
    )
    assert result.status == 'failed', result.to_dict(include_details=True)
    assert result.files[0].failures[0].kind == 'SequenceError'
    assert not result.files[0].outputs
    assert previous.read_bytes() == b'original'
    assert list(previous.parent.iterdir()) == [previous]


@pytest.mark.parametrize('options', [
    {'max_sequence_frames': 0}, {'sequence_memory_bytes': False},
])
def test_sequence_limits_reject_invalid_types(animation, options):
    from phatch.core.sequences import SequenceError, inspect_sequence

    with pytest.raises(SequenceError, match='positive integers'):
        inspect_sequence(animation, options)


def test_conflicting_sequence_fields_fail_before_batch_outputs(tmp_path, animation):
    from phatch.core.sequences import SequenceError, workflow_settings

    actions = [*workflow(tmp_path), *workflow(tmp_path)]
    actions[0].set_field_as_string('Animation Policy', 'first')
    actions[1].set_field_as_string('Animation Policy', 'extract')
    with pytest.raises(SequenceError, match='Conflicting'):
        workflow_settings(actions, {})
    result = run_batch(actions, [animation])
    assert result.status == 'invalid_setup'
    assert not (tmp_path / 'outputs').exists()
    actions[0].set_field_as_string('__enabled__', 'no')
    assert workflow_settings(actions, {})['animation_policy'] == 'extract'


def test_invalid_sequence_policy_is_actionable(animation):
    from phatch.core.sequences import SequenceError, inspect_sequence, policy_for

    with pytest.raises(SequenceError, match='Expected'):
        policy_for(inspect_sequence(animation, {}), {'animation_policy': 'unknown'})

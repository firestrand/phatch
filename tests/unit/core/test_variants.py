"""Variant outputs use independent source pixels and participate in batch contracts."""

import json

import pytest
from PIL import Image

from phatch.core import api
from phatch.core.batch import plan_batch, run_batch
from phatch.core.variants import (
    Variant,
    VariantValidationError,
    parse_variants,
    variant_action,
    web_preset,
)


@pytest.fixture
def source(tmp_path):
    path = tmp_path / 'source.png'
    with Image.new('RGB', (120, 60)) as image:
        image.putdata(
            [(x * 17 % 256, x * 31 % 256, x * 47 % 256) for x in range(7200)]
        )
        image.save(path)
    return path


def action(tmp_path, variants):
    api.import_actions()
    return variant_action(variants, tmp_path / 'outputs')


def test_independent_sizes_and_manifest(tmp_path, source):
    variants = [
        Variant('tiny', 20, 20, 'png'),
        Variant('large', 100, 100, 'png'),
        Variant('original', 500, 500, 'png'),
    ]
    workflow = [action(tmp_path, variants)]
    plan = plan_batch(workflow, [source])
    assert plan.valid, plan.issues
    assert len(plan.files[0].destinations) == 4
    assert plan.files[0].destinations[-1].artifact
    assert not (tmp_path / 'outputs').exists()
    result = run_batch(workflow, [source])
    assert result.status == 'success', result.to_dict(include_details=True)
    assert len(result.files[0].outputs) == 3
    assert len(result.files[0].artifacts) == 1
    with Image.open(source) as original:
        for path, size in zip(
            result.files[0].outputs, [(20, 10), (100, 50), (120, 60)]
        ):
            with Image.open(path) as output:
                expected = original.resize(size, Image.Resampling.LANCZOS)
                assert output.size == size
                assert output.tobytes() == expected.tobytes()
                expected.close()
    manifest = json.loads(result.files[0].artifacts[0].read_text())
    assert manifest['source']['name'] == source.name
    assert [v['path'] for v in manifest['variants']] == [
        p.name for p in result.files[0].outputs
    ]
    assert [(v['width'], v['height']) for v in manifest['variants']] == [
        (20, 10),
        (100, 50),
        (120, 60),
    ]
    assert all(v['status'] == 'committed' for v in manifest['variants'])


def test_explicit_upscale_and_web_defaults():
    assert Variant('large', 240, 240, no_upscale=False).size_for(
        (120, 60)
    ) == (240, 120)
    preset = web_preset()
    assert len(preset) == 6
    assert {v.format for v in preset} == {'webp', 'avif'}
    assert all(
        v.no_upscale
        and v.metadata_policy == 'sharing'
        and v.color_policy == 'srgb'
        for v in preset
    )


@pytest.mark.parametrize('workers', [1, 2])
def test_skipped_extracted_variants_reference_existing_frame_paths(
    tmp_path, workers
):
    source = tmp_path / 'moving.gif'
    frames = [Image.new('RGB', (16, 10), color) for color in ('red', 'blue')]
    try:
        frames[0].save(
            source, save_all=True, append_images=frames[1:], duration=[40, 80]
        )
    finally:
        for frame in frames:
            frame.close()
    workflow = [action(tmp_path, [Variant('tiny', 8, 8, 'png')])]
    settings = {'animation_policy': 'extract', 'workers': workers}
    first = run_batch(workflow, [source], settings)
    assert first.status == 'success', first.to_dict(include_details=True)
    originals = {path: path.read_bytes() for path in first.files[0].outputs}
    for artifact in first.files[0].artifacts:
        artifact.unlink()
    skipped = run_batch(
        workflow, [source], {**settings, 'collision_policy': 'skip'}
    )
    assert skipped.status == 'success', skipped.to_dict(include_details=True)
    assert not skipped.files[0].outputs
    assert len(skipped.files[0].artifacts) == 2
    associated = []
    for artifact in skipped.files[0].artifacts:
        payload = json.loads(artifact.read_text())
        for record in payload['variants']:
            assert record['status'] == 'skipped'
            path = artifact.parent / record['path']
            associated.append(path)
            assert path.read_bytes() == originals[path]
    assert associated == list(originals)


@pytest.mark.parametrize(
    'value',
    [
        '[]',
        '{}',
        '[1]',
        '[{"name":"bad"}]',
        '[{"name":"a","width":true,"height":2}]',
        '[{"name":"../bad","width":1,"height":2}]',
    ],
)
def test_invalid_definitions(value):
    with pytest.raises(VariantValidationError):
        parse_variants(value)


def test_duplicate_names_rejected():
    value = json.dumps(
        [{'name': name, 'width': 1, 'height': 1} for name in ['same', 'SAME']]
    )
    with pytest.raises(VariantValidationError, match='duplicate'):
        parse_variants(value)


def test_resume_requires_variant_artifact(tmp_path, source):
    workflow = [action(tmp_path, [Variant('small', 20, 20, 'png')])]
    settings = {'manifest_path': tmp_path / 'job.json'}
    initial = run_batch(workflow, [source], settings)
    assert initial.status == 'success', initial.to_dict(include_details=True)
    resumed = run_batch(workflow, [source], {**settings, 'resume': True})
    assert resumed.files[0].resumed
    assert resumed.files[0].artifacts == initial.files[0].artifacts
    initial.files[0].artifacts[0].unlink()
    refreshed = run_batch(workflow, [source], {**settings, 'resume': True})
    assert refreshed.status == 'success'
    assert not refreshed.files[0].resumed
    assert refreshed.files[0].artifacts[0].is_file()


def test_collision_and_report_protection(tmp_path, source):
    workflow = [action(tmp_path, [Variant('small', 20, 20, 'png')])]
    duplicate = tmp_path / 'other' / source.name
    duplicate.parent.mkdir()
    duplicate.write_bytes(source.read_bytes())
    assert not plan_batch(workflow, [source, duplicate]).valid
    result = run_batch(workflow, [source])
    artifact = result.files[0].artifacts[0]
    before = artifact.read_bytes()
    with pytest.raises(ValueError, match='overlaps'):
        result.write_report(artifact)
    assert artifact.read_bytes() == before


def test_cancel_between_variants_preserves_committed_output(tmp_path, source):
    workflow = [
        action(
            tmp_path,
            [
                Variant('first', 20, 20, 'png'),
                Variant('second', 40, 40, 'png'),
            ],
        )
    ]
    first = tmp_path / 'outputs/source-first.png'
    result = run_batch(workflow, [source], cancel=first.exists)
    assert result.status == 'cancelled', result.to_dict(include_details=True)
    assert result.files[0].outputs == [first]
    assert not result.files[0].artifacts
    assert not (tmp_path / 'outputs/source-second.png').exists()


def test_later_encoder_failure_retains_prior_output(
    tmp_path, source, monkeypatch
):
    from phatch.core import pil

    workflow = [
        action(
            tmp_path,
            [
                Variant('first', 20, 20, 'png'),
                Variant('second', 40, 40, 'png'),
            ],
        )
    ]
    original = pil.Photo.save

    def fail_second(self, filename, **kwargs):
        if 'second' in filename:
            raise OSError('injected encoder failure')
        return original(self, filename, **kwargs)

    monkeypatch.setattr(pil.Photo, 'save', fail_second)
    result = run_batch(workflow, [source])
    assert result.status == 'partial_failure'
    assert [p.name for p in result.files[0].outputs] == ['source-first.png']
    assert result.files[0].failures[0].kind == 'OSError'
    assert not result.files[0].artifacts


def test_explicit_fallback_agrees_with_preflight(
    tmp_path, source, monkeypatch
):
    from phatch.core import capabilities

    original = capabilities.encoder_available
    monkeypatch.setattr(
        capabilities,
        'encoder_available',
        lambda encoder: encoder != 'AVIF' and original(encoder),
    )
    workflow = [action(tmp_path, [Variant('small', 20, 20, 'avif')])]
    assert not plan_batch(workflow, [source]).valid
    workflow[0].set_field_as_string('Format Fallback', 'png')
    plan = plan_batch(workflow, [source])
    assert plan.valid
    result = run_batch(workflow, [source])
    assert result.status == 'success', result.to_dict(include_details=True)
    assert result.files[0].outputs[0] == plan.files[0].destinations[0].path
    assert result.files[0].outputs[0].suffix == '.png'


def test_renamed_outputs_record_actual_paths(tmp_path, source):
    workflow = [action(tmp_path, [Variant('small', 20, 20, 'png')])]
    initial = run_batch(workflow, [source])
    workflow[0].set_field_as_string('Collision Policy', 'rename')
    plan = plan_batch(workflow, [source])
    result = run_batch(workflow, [source])
    assert result.status == 'success'
    assert result.files[0].outputs[0] == plan.files[0].destinations[0].path
    assert result.files[0].artifacts[0] == plan.files[0].destinations[1].path
    assert initial.files[0].outputs[0] != result.files[0].outputs[0]
    manifest = json.loads(result.files[0].artifacts[0].read_text())
    assert manifest['variants'][0]['path'] == result.files[0].outputs[0].name


def test_variant_artifact_cannot_overlap_batch_report(tmp_path, source):
    workflow = [action(tmp_path, [Variant('small', 20, 20, 'png')])]
    result = run_batch(
        workflow,
        [source],
        {'report_path': tmp_path / 'outputs/source-variants.json'},
    )
    assert result.status == 'invalid_setup'
    assert any(issue.code == 'artifact_collision' for issue in result.issues)
    assert not (tmp_path / 'outputs').exists()


@pytest.mark.parametrize('format', ['jpeg', 'png', 'webp', 'avif', 'tiff'])
def test_variant_metadata_and_profile_policy(tmp_path, format):
    from PIL import ImageCms
    from phatch.core.capabilities import encoder_available

    variant = Variant('sharing', 40, 40, format)
    if not encoder_available(variant.encoder):
        pytest.skip(f'{format} encoder unavailable')
    source = tmp_path / 'private.png'
    exif = Image.Exif()
    exif[315] = 'Private artist'
    exif[271] = 'Private camera'
    exif[274] = 6
    profile = ImageCms.ImageCmsProfile(
        ImageCms.createProfile('sRGB')
    ).tobytes()
    with Image.new('RGB', (120, 60), 'red') as image:
        image.save(source, exif=exif, icc_profile=profile)
    result = run_batch([action(tmp_path, [variant])], [source])
    assert result.status == 'success', result.to_dict(include_details=True)
    with Image.open(result.files[0].outputs[0]) as output:
        output.load()
        assert output.size == (20, 40)
        assert not output.getexif().get(315)
        assert not output.getexif().get(271)
        assert output.getexif().get(274, 1) == 1
        assert output.info.get('icc_profile')


def test_bundled_preset_recipe_loads():
    from pathlib import Path

    api.import_actions()
    recipe, warning = api.open_actionlist(
        str(
            Path(__file__).resolve().parents[3]
            / 'phatch_assets/data/actionlists/web_variants.phatch'
        )
    )
    assert recipe['actions'][0].label == 'Variants'
    assert recipe['actions'][0].get_field_string('Preset') == 'web'


@pytest.mark.parametrize('workers', [1, 2])
@pytest.mark.parametrize('sequence_policy', ['first', 'extract'])
@pytest.mark.parametrize('skipped_kind', ['image', 'artifact'])
@pytest.mark.parametrize('mutation', ['delete', 'change'])
def test_mixed_collision_skips_never_become_verified_resume(
    tmp_path, source, workers, sequence_policy, skipped_kind, mutation
):
    if sequence_policy == 'extract':
        source = tmp_path / 'animated.gif'
        frames = [
            Image.new('RGB', (40, 20), color) for color in ('red', 'blue')
        ]
        try:
            frames[0].save(source, save_all=True, append_images=frames[1:])
        finally:
            for frame in frames:
                frame.close()
    workflow = [
        action(
            tmp_path,
            [Variant('tiny', 10, 10, 'png'), Variant('large', 30, 30, 'png')],
        )
    ]
    settings = {'workers': workers, 'animation_policy': sequence_policy}
    initial = run_batch(workflow, [source], settings)
    assert initial.status == 'success', initial.to_dict(include_details=True)
    paths = initial.files[0].outputs + initial.files[0].artifacts
    skipped = (
        initial.files[0].outputs[0]
        if skipped_kind == 'image'
        else initial.files[0].artifacts[0]
    )
    original_bytes = skipped.read_bytes()
    for path in paths:
        if path != skipped:
            path.unlink()
    journal = tmp_path / 'job.json'
    settings.update(manifest_path=journal, collision_policy='skip')
    mixed = run_batch(workflow, [source], settings)
    assert mixed.status == 'success', mixed.to_dict(include_details=True)
    assert skipped.read_bytes() == original_bytes
    assert skipped not in mixed.files[0].outputs + mixed.files[0].artifacts
    assert (
        json.loads(journal.read_text())['records'][str(source)]['status']
        == 'incomplete'
    )
    if mutation == 'delete':
        skipped.unlink()
    elif skipped_kind == 'image':
        with Image.new('RGB', (10, 5), 'green') as replacement:
            replacement.save(skipped)
    else:
        skipped.write_text('{"unrelated": true}\n')
    resumed = run_batch(workflow, [source], {**settings, 'resume': True})
    assert resumed.status == 'success', resumed.to_dict(include_details=True)
    assert not resumed.files[0].resumed
    assert skipped.is_file()
    if mutation == 'delete':
        assert skipped in resumed.files[0].outputs + resumed.files[0].artifacts


@pytest.mark.parametrize('workers', [1, 2])
def test_fully_committed_renamed_variants_remain_resumable(
    tmp_path, source, workers
):
    workflow = [action(tmp_path, [Variant('small', 20, 20, 'png')])]
    settings = {'workers': workers}
    initial = run_batch(workflow, [source], settings)
    assert initial.status == 'success'
    workflow[0].set_field_as_string('Collision Policy', 'rename')
    settings['manifest_path'] = tmp_path / 'job.json'
    renamed = run_batch(workflow, [source], settings)
    assert renamed.status == 'success', renamed.to_dict(include_details=True)
    assert renamed.files[0].outputs != initial.files[0].outputs
    resumed = run_batch(workflow, [source], {**settings, 'resume': True})
    assert resumed.status == 'success', resumed.to_dict(include_details=True)
    assert resumed.files[0].resumed
    assert resumed.files[0].outputs == renamed.files[0].outputs
    assert resumed.files[0].artifacts == renamed.files[0].artifacts

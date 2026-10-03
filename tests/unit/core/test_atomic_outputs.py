# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Data-integrity regressions using the repository's real input image."""

from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from phatch.core import api, pil
from phatch.lib.atomic import AtomicOutput, observe_outputs


def test_failed_output_registration_cleans_temp_and_restores_observer(
    tmp_path,
):
    target = tmp_path / 'photo.png'
    target.write_bytes(b'original')

    def reject(phase, temporary, destination):
        assert phase == 'created'
        assert temporary.exists()
        assert destination == target
        raise RuntimeError('registration failed')

    with pytest.raises(RuntimeError, match='registration failed'):
        with observe_outputs(reject), AtomicOutput(target):
            pytest.fail('Encoding must wait for registration')
    assert list(tmp_path.iterdir()) == [target]
    assert target.read_bytes() == b'original'
    with AtomicOutput(target) as temporary:
        temporary.write_bytes(b'new')
    assert target.read_bytes() == b'new'


@pytest.fixture
def photo(test_input_dir, monkeypatch):
    monkeypatch.setattr(pil, '_t', str)
    monkeypatch.setattr(api, '_', str, raising=False)
    image = Image.open(test_input_dir / 'frog.gif').convert('RGB')
    # Exercise the real save method without optional metadata initialization.
    instance = pil.Photo.__new__(pil.Photo)
    instance.modify_date = None
    instance._exif_transposition_reverse = ()
    instance.report_files = []
    instance.info = {'path': str(test_input_dir / 'frog.gif')}
    instance.get_flattened_image = lambda: image
    instance.log = lambda message: None
    yield instance
    image.close()


def test_failed_encoding_preserves_original(photo, tmp_path):
    target = tmp_path / 'photo.png'
    photo.get_flattened_image().save(target)
    original = target.read_bytes()

    def fail(image, filename, **options):
        Path(filename).write_bytes(b'partial encoding')
        raise OSError('encoder failed')

    with patch.object(pil.imtools, 'save_check_mode', side_effect=fail):
        with pytest.raises(OSError, match='encoder failed'):
            photo.save(str(target), save_metadata=False)
    assert target.read_bytes() == original
    assert list(tmp_path.iterdir()) == [target]
    assert photo.report_files == []


def test_failed_metadata_preserves_original(photo, tmp_path):
    target = tmp_path / 'photo.jpg'
    photo.get_flattened_image().save(target)
    original = target.read_bytes()

    class Metadata(dict):
        def save(self, filename, **kwargs):
            raise OSError('metadata failed')

    photo.info = Metadata(photo.info)
    with (
        patch.object(pil, 'exif') as backend,
        patch.object(pil.imtools, 'get_format_data', return_value=b''),
    ):
        backend.is_writable_format.return_value = True
        with pytest.raises(OSError, match='metadata failed'):
            photo.save(str(target))
    assert target.read_bytes() == original
    assert list(tmp_path.iterdir()) == [target]


def test_successful_save_commits_and_reports(photo, tmp_path):
    target = tmp_path / 'photo.png'
    photo.save(str(target), save_metadata=False)
    with Image.open(target) as result:
        result.load()
        assert result.size == photo.get_flattened_image().size
    assert len(photo.report_files) == 1
    assert list(tmp_path.iterdir()) == [target]


def test_failed_recipe_serialization_preserves_original(tmp_path):
    target = tmp_path / 'recipe.phatch'
    original = Path('data/actionlists/resize.phatch').read_bytes()
    target.write_bytes(original)
    with patch.object(api.json, 'dump', side_effect=OSError('disk full')):
        with pytest.raises(OSError, match='disk full'):
            api.save_actionlist(
                str(target), {'actions': [], 'description': ''}
            )
    assert target.read_bytes() == original
    assert list(tmp_path.iterdir()) == [target]


def test_recipe_save_does_not_mutate_caller(tmp_path):
    payload = {'description': 'A recipe', 'actions': []}
    api.save_actionlist(str(tmp_path / 'recipe'), payload)
    assert payload == {'description': 'A recipe', 'actions': []}


@pytest.mark.parametrize('policy', ['skip', 'fail', 'replace', 'rename'])
def test_collision_at_commit_preserves_competing_writer(tmp_path, policy):
    from phatch.lib.atomic import AtomicOutput

    target = tmp_path / 'output.txt'
    transaction = AtomicOutput(target, policy)
    try:
        with transaction as temporary:
            temporary.write_text('new output')
            # Another writer wins after our transaction starts.
            target.write_text('competing output')
    except FileExistsError:
        assert policy == 'fail'
    if policy == 'replace':
        assert target.read_text() == 'new output'
    else:
        assert target.read_text() == 'competing output'
    if policy == 'rename':
        assert transaction.committed == tmp_path / 'output-1.txt'
        assert transaction.committed.read_text() == 'new output'
    assert not list(tmp_path.glob('.*'))


def test_explicit_encoder_is_preserved(photo, tmp_path):
    target = tmp_path / 'output.jpg'
    photo.save(target, format='PNG', save_metadata=False)
    with Image.open(target) as image:
        assert image.format == 'PNG'


def test_failed_validation_preserves_original(photo, tmp_path):
    target = tmp_path / 'output.png'
    photo.get_flattened_image().save(target)
    original = target.read_bytes()
    with patch.object(pil.imtools, 'save_check_mode', return_value=''):
        with pytest.raises(OSError):
            photo.save(target, save_metadata=False)
    assert target.read_bytes() == original


def test_successful_recipe_save_retains_backup(tmp_path):
    target = tmp_path / 'recipe.phatch'
    original = Path('data/actionlists/resize.phatch').read_bytes()
    target.write_bytes(original)
    api.save_actionlist(str(target), {'actions': [], 'description': ''})
    assert target.with_name('recipe.phatch~').read_bytes() == original

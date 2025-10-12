import os

from phatch.lib import unicoding


def test_fix_filename_returns_none_for_missing_non_ascii():
    # Should not raise TypeError when probing alternative encodings
    assert unicoding.fix_filename('nonexistent-é.png') is None


def test_fix_filename_handles_bytes_path(tmp_path):
    path = tmp_path / 'hé.png'
    path.write_text('data', encoding='utf-8')
    byte_path = os.fsencode(str(path))
    assert unicoding.fix_filename(byte_path) == str(path)
